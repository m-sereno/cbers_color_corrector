# 🛰️🖼️ CBERS Color Corrector

## Description

CBERS Color Corrector is a QGIS plugin that aims to improve the quality of CBERS images by correcting their colors to match a reference dataset. This reference data is composed of CBERS images that have already been corrected by the DSG, Brazilian Army.

## Features

1. Automatically correct the color distribution for a CBERS image, provided that it has already undergone the pansharpening process.

## Installation

1. Open QGIS.
2. Navigate to `Plugins` > `Manage and Install Plugins...`.
3. In the `Search` bar, type `CBERS Color Corrector`.
4. Click `Install Plugin`.

## Usage

1. After installation, navigate to `Raster` > `CBERS Color Corrector`.
2. A dialog box will prompt you to select an image file or a raster layer.
3. Specify your preferred output instructions for the generated raster after the treatment.
4. Click `Submit`.
5. The plugin will then split the image into many tiles, calculate the CDF and embedding vector for each tile, and send this information to the server.
6. The server responds with a correction function based on the best matching tile pairs and their histogram matching functions.
7. The plugin applies this function to the image to generate the corrected output.

## Contributing

We welcome any contributions to the CBERS Color Corrector project. Please feel free to submit a pull request or open an issue.

## License

This project is licensed under the MIT License - see the LICENSE file for more details.

## Contact

If you have any questions, feedback, or issues, please feel free to contact us.
