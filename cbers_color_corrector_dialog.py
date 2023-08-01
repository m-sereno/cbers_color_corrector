# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CBERSColorCorrectorDialog
                                 A QGIS plugin
 This plugin corrects the color from CBERS images to match the database
                             -------------------
        begin                : 2023-05-27
        git sha              : $Format:%H$
        copyright            : (C) 2023 by Mateus Sereno
        email                : mateus.sereno@ime.eb.br
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

import numpy as np
import requests
from typing import List

from qgis.core import QgsRasterLayer, QgsProject
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.core import QgsProject, QgsMapLayerType, QgsMessageLog, QgsRasterLayer, QgsRectangle, QgsRasterBlock, Qgis
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QDialog, QComboBox

class TileHistogram():
    def __init__(self, r_hist : np.ndarray, g_hist : np.ndarray, b_hist : np.ndarray):
        self.r_hist = r_hist
        self.g_hist = g_hist
        self.b_hist = b_hist

class TileCdf():
    def __init__(self, r_cdf : np.ndarray, g_cdf : np.ndarray, b_cdf : np.ndarray):
        self.r_cdf = r_cdf
        self.g_cdf = g_cdf
        self.b_cdf = b_cdf

class HistMatchingFunction():
    def __init__(self, r_func : np.ndarray, g_func : np.ndarray, b_func : np.ndarray):
        self.r_func = r_func
        self.g_func = g_func
        self.b_func = b_func

class BestMatchRequest():
    def __init__(self, embedding: np.ndarray):
        self.embedding = embedding

class BestMatchResponse():
    def __init__(self, best_match_cdf: TileCdf, similarity: float):
        self.best_match_cdf = best_match_cdf
        self.similarity = similarity


# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'cbers_color_corrector_dialog_base.ui'))

class CBERSColorCorrectorDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(CBERSColorCorrectorDialog, self).__init__(parent)
        self.setupUi(self)

        self.populate_combobox()
        self.button_box.accepted.connect(self.on_ok_clicked)

        self.all_histograms = list()
        self.diverse_histograms = list()
    
    def euclidean_distance(self, v1, v2):
        """Calculate the Euclidean distance between two vectors."""
        return np.sqrt(np.sum((v1 - v2) ** 2))
    
    def tile_hist_distance(self, h1 : TileHistogram, h2 : TileHistogram):
        """Calculate the Distance between two tile histograms."""
        dist_r = self.euclidean_distance(h1.r_hist, h2.r_hist)
        dist_g = self.euclidean_distance(h1.g_hist, h2.g_hist)
        dist_b = self.euclidean_distance(h1.b_hist, h2.b_hist)

        return dist_r + dist_g + dist_b
    
    def find_most_diverse(self, M):
        """Find the M most diverse vectors from the list."""
        
        # Create a copy of the list so we can modify it
        hists = list(self.all_histograms)
        
        # Start with a randomly chosen histogram
        diverse_picks = [hists.pop(np.random.randint(len(hists)))]

        # Repeat until we have selected M histograms
        while len(diverse_picks) < M:
            # For each tile histogram, calculate the minimum distance to the selected ones
            min_distances = [min(self.tile_hist_distance(self, v, selected) for selected in diverse_picks)
                            for v in hists]
            
            # Select the vector with the maximum minimum distance
            diverse_picks.append(hists.pop(np.argmax(min_distances)))

        return diverse_picks
    
    def get_histogram_matching_function_band(self, cdf1_band : np.ndarray, cdf2_band : np.ndarray):
        matching_function_band = np.zeros_like(cdf1_band)

        for i in range(256):
            diff = np.abs(cdf1_band[i] - cdf2_band[i])
            idx = np.argmin(diff)
            matching_function_band[i] = idx

        return matching_function_band
    
    def get_histogram_matching_function(self, cdf1 : TileCdf, cdf2 : TileCdf):
        matching_function = HistMatchingFunction()

        matching_function.r_func = self.get_histogram_matching_function_band(cdf1.r_cdf, cdf2.r_cdf)
        matching_function.g_func = self.get_histogram_matching_function_band(cdf1.g_cdf, cdf2.g_cdf)
        matching_function.b_func = self.get_histogram_matching_function_band(cdf1.b_cdf, cdf2.b_cdf)

        return matching_function
    
    def compute_average_function(self, hist_matching_functions : List[HistMatchingFunction]):
        avg_f = HistMatchingFunction()

        for value in range(256):
            avg_f.r_func = np.mean([func[value].r_func for func in hist_matching_functions])
            avg_f.g_func = np.mean([func[value].g_func for func in hist_matching_functions])
            avg_f.b_func = np.mean([func[value].b_func for func in hist_matching_functions])

        return avg_f

    def populate_combobox(self):
        """Populate the combo box with available raster layers."""
        layers = QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == QgsMapLayerType.RasterLayer:
                self.selectLayerComboBox.addItem(layer.name())
    
    def on_ok_clicked(self):
        """Handle the OK button click."""
        selected_layer = self.selectLayerComboBox.currentText()
        QgsMessageLog.logMessage(f'Selected layer: {selected_layer}', "CBERSColorCorrector", Qgis.Info)

        # Load the raster
        layer = QgsProject.instance().mapLayersByName(selected_layer)[0]
        
        width = layer.width()
        height = layer.height()

        provider = layer.dataProvider()

        for y_start in range(0, width, 512):
            for x_start in range(0, height, 512):
                
                # Define the extent of the current tile:
                extent = QgsRectangle(
                    layer.extent().xMinimum() + x_start * layer.rasterUnitsPerPixelX(),
                    layer.extent().yMinimum() + y_start * layer.rasterUnitsPerPixelY(),
                    layer.extent().xMinimum() + (x_start + 512) * layer.rasterUnitsPerPixelX(),
                    layer.extent().yMinimum() + (y_start + 512) * layer.rasterUnitsPerPixelY()
                )

                # Calculate the histogram
                tile_hist = TileHistogram()
                hist_list = list()

                for band_index in range(1, 4):

                    # Read tile data:
                    tile : QgsRasterBlock = provider.block(band_index, extent, 512, 512)
                    data = tile.data()

                    # Compute histogram:
                    histogram, bin_edges = np.histogram(data, bins=256, range=(0, 256))
                    hist_list.append(histogram)
                
                tile_hist.r_hist = hist_list[0]
                tile_hist.g_hist = hist_list[1]
                tile_hist.b_hist = hist_list[2]

                self.all_histograms.append(tile_hist)
        
        self.diverse_histograms = self.find_most_diverse(20)

        hist_matching_functions = []

        for hist_index in range(0, len(self.diverse_histograms)):
            hist : TileHistogram = self.diverse_histograms[hist_index]
            cdf = TileCdf()
            cdf.r_cdf = np.cumsum(hist.r_hist)
            cdf.g_cdf = np.cumsum(hist.g_hist)
            cdf.b_cdf = np.cumsum(hist.b_hist)

            # TODO: CALCULATE EMBEDDING.

            best_match_req = BestMatchRequest()

            url = 'https://server-url/endpoint'

            res = requests.post(url, json=best_match_req)
            best_match_res : BestMatchResponse = res.json()

            res_cdf = best_match_res.best_match_cdf

            hist_mapping_f = self.get_histogram_matching_function(cdf, res_cdf)
            hist_matching_functions.append(hist_mapping_f)

        avg_hist_matching_f = self.compute_average_function(hist_matching_functions)

        # TODO: Apply the function to the original image.
        # TODO: The result will appear as a new raster layer.