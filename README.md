# Chord Diagram Generator

This Python script generates visual diagrams of musical chords based on specified root notes, types, and inversions, or from a list of specific chord names. It can output the diagrams into a single multi-page PDF file or as individual image files (PNG or JPG).

![Example Chord Diagram](examples/B_maj7_Inversion_2.png)

## Features

* **Flexible Input:** Generate diagrams using either:
    * Combinations of roots, types, and inversions (e.g., all major and minor chords for C, F, G).
    * A specific list of chord names, including slash notation for inversions (e.g., `Cmaj7`, `G7/B`, `Am`, `Fsus4`).
* **Comprehensive Chord Vocabulary:** Supports a wide range of chord types:
    * Major, Minor, Augmented, Diminished triads
    * Dominant 7th, Major 7th, Minor 7th, Diminished 7th, Half-diminished 7th (m7b5)
    * Major 6th, Minor 6th
    * Major 9th, Dominant 9th, Minor 9th
    * Suspended 2nd, Suspended 4th
    * Parses common aliases (e.g., `m`, `min`, `M`, `maj`, `dom7`, `o`, `+`, `sus`, `ø`).
* **Inversion Handling:** Automatically calculates and displays specified inversions (0 for root, 1 for first, etc.), including parsing from slash notation (e.g., `C/E` is C major, 1st inversion).
* **Multiple Output Formats:**
    * `pdf`: Creates a single, multi-page PDF file containing all generated diagrams. The PDF is named descriptively based on the input chords/combinations.
    * `png` / `jpg`: Creates individual image files for each diagram. These images are saved within a descriptively named *subdirectory*.
* **Clear Visualization:** Distinguishes between white and black keys and clearly labels notes. Diagram width adjusts slightly for chords with more notes.
* **Customizable Output Location:** Specify a base directory for all output.

## Installation

1.  **Clone the Repository (or download the files):**
    ```bash
    git clone <your-repo-url>
    cd <repository-directory>
    ```

2.  **Install System Dependency: Graphviz**
    While Matplotlib handles the final rendering, the underlying `networkx` library sometimes benefits from having the Graphviz layout engine installed on your system.
    * **macOS (using Homebrew):**
        ```bash
        brew install graphviz
        ```
    * **Linux (Debian/Ubuntu):**
        ```bash
        sudo apt-get update
        sudo apt-get install graphviz libgraphviz-dev pkg-config
        ```
    * **Windows:** Download the installer from the official [Graphviz Download Page](https://graphviz.org/download/) and ensure its `bin` directory is added to your system's PATH environment variable.

3.  **Install Python Dependencies:**
    Using a virtual environment is recommended:
    ```bash
    python -m venv venv
    # Activate the environment (use `venv\Scripts\activate` on Windows)
    source venv/bin/activate
    ```
    Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
    The `requirements.txt` file should contain:
    ```
    matplotlib
    networkx
    ```

## Usage

Run the script from your terminal. You must choose **one** input mode:

**Mode 1: Specify Individual Chords**

Use the `-c` or `--chords` flag followed by a list of chord names.

```bash
python chord_generator.py -c <chord1> [<chord2> ...] [OPTIONS]
```

Chord names can include root (C, F#, etc.), type suffix (maj7, m, aug, sus4, 9, etc.), and optional slash notation for bass note/inversion (e.g., `/E`).
See `CHORD_TYPE_MAP` in the script for supported aliases (e.g., `m`, `min`, `M`, `maj`, `o`,`+`, `ø`).

**Mode 2: Generate Combinations**

Use flags like `-r`, `-t`, `-i` to specify lists of roots, types, and inversions. If `-c` is not used, this mode is active.

```bash
python chord_generator.py [-r <roots...>] [-t <types...>] [-i <inversions...>] [--skip-root] [OPTIONS]
```

**Common Options (Applicable to both modes):**

`--format <format>`: Output format. Choices: `pdf` (default), `png`, `jpg`.
`--output-dir <directory>`: Base directory to save output. Default: `./chord_graphs`.
If format is `pdf`, the PDF file is saved directly in this directory (e.g., `./chord_graphs/MyChords.pdf`).
If format is `png` or `jpg`, a subdirectory is created inside `--output-dir` (e.g., `./chord_graphs/MyChords/`), and individual image files are saved there.
`-h`, `--help`: Show the detailed help message and exit.

**Examples:**

1. Generate default combinations as PDF (in `./chord_graphs/`):

```bash
python chord_generator.py
```
_(Output: ./chord_graphs/Roots_All_Types_All_Invs_Default.pdf)_

2. Generate specific chords ("Cmaj7", "G7/B", "Am") as PNGs:

```bash
python chord_generator.py -c Cmaj7 G7/B Am --format png
```
_(Output: Individual PNG files inside ./chord_graphs/CustomChords-Cmaj7-G7_B-Am/)_

3. Generate C and F minor 7th chords (root & 1st inversion) as JPGs in a specific directory:

```bash
python chord_generator.py -r C F -t m7 -i 0 1 --format jpg --output-dir ./output_images
```
_(Output: Individual JPG files inside ./output_images/Roots_C-F_Type_m7_Invs_0-1/)_

4. Generate Fsus4 and C augmented chords as a PDF:

```bash
python chord_generator.py -c Fsus4 Caug --format pdf --output-dir .
```
_(Output: ./CustomChords-Fsus4-Caug.pdf)_
