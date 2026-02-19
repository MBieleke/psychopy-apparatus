# psychopy-apparatus
PsychoPy plugin to control the "Apparatus," a custom device for measuring and manipulating physical and cognitive effort.

## Installation

- Install Psychopy 2025.2.1 or later. Earlier versions will not work.
    - As of December 2025, versions later than 2025.1.1 have a bug regarding the plugin manager. You have to install 2025.1.1 first, start it and open the plugin manager once. Afterwards, you can install a 2025.2.x version.
- Clone this repository using Git or download the source code manually.
- Go to Plugins & Packages Manager in Builder. In the "Packages" tab, click click the "Install from file" button and select the `pyproject.toml` file for your plugin (you will need to change the file type dropdown to look for "Python projects" rather than a "Wheel files" to see it).
