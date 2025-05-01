# chord_generator.py
# -*- coding: utf-8 -*-
"""Generates musical chord diagrams as PDF or individual image files (PNG/JPG).

This script visualizes musical chords specified either through combinations of
roots, types, and inversions, or by providing a list of specific chord names
(including optional slash notation for inversions like 'G7/B').

Features:
  - Supports various chord types: major, minor, dominant 7th, maj7, min7,
    diminished, augmented, suspended, 6ths, 9ths, etc.
  - Handles all 12 chromatic root notes.
  - Parses common chord notation including aliases (m, min, maj, M, dim, o, aug, +)
    and slash notation for inversions (e.g., C/E).
  - Outputs diagrams to a specified directory.
  - Output formats: Multi-page PDF, or individual PNG/JPG files (saved in a
    descriptively named subdirectory).
  - Customizable via command-line arguments.

Dependencies:
  - matplotlib
  - networkx

Example Usage:
  # Default: Generate common chords as PDF in './chord_graphs/'
  python chord_generator.py

  # Generate specific chords as PNG files in './my_song_chords/'
  python chord_generator.py -c Cmaj7 G7/B Am Fsus4 --format png --output-dir ./my_song_chords/

  # Generate C and F minor and dominant 7th chords (root & 1st inv) as JPGs
  # Output dir: ./chord_graphs/Roots_C-F_Types_minor-7_Invs_0-1/
  python chord_generator.py -r C F -t m 7 -i 0 1 --format jpg
"""

import itertools
import argparse
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.backends.backend_pdf import PdfPages
import logging
import re
import os
from typing import List, Tuple, Optional, Dict

# --- Basic Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__) # Use a named logger

# --- Musical Constants ---
CHROMATIC_SCALE: List[str] = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
KEY_TYPES: List[str] = ["white", "black", "white", "black", "white", "white", "black", "white", "black", "white", "black", "white"]

# Chord Definitions: Internal Name -> List of intervals (in semitones from root)
# Intervals > 11 represent notes in the next octave (e.g., 14 is a 9th)
INTERVALS: Dict[str, List[int]] = {
    # Basic Triads
    "major":    [0, 4, 7],       # R, M3, P5
    "minor":    [0, 3, 7],       # R, m3, P5
    "aug":      [0, 4, 8],       # R, M3, A5 (Augmented)
    "dim":      [0, 3, 6],       # R, m3, d5 (Diminished)
    # Suspended
    "sus4":     [0, 5, 7],       # R, P4, P5
    "sus2":     [0, 2, 7],       # R, M2, P5
    # Sevenths
    "7":        [0, 4, 7, 10],   # R, M3, P5, m7 (Dominant 7th)
    "maj7":     [0, 4, 7, 11],   # R, M3, P5, M7 (Major 7th)
    "minor7":   [0, 3, 7, 10],   # R, m3, P5, m7 (Minor 7th)
    "dim7":     [0, 3, 6, 9],    # R, m3, d5, d7 (Diminished 7th - d7 is 9 semitones)
    "m7b5":     [0, 3, 6, 10],   # R, m3, d5, m7 (Half-diminished 7th)
    # Sixths
    "6":        [0, 4, 7, 9],    # R, M3, P5, M6 (Major 6th)
    "minor6":   [0, 3, 7, 9],    # R, m3, P5, M6 (Minor 6th)
    # Ninths (Based on adding M9 (14) to 7th chords)
    "maj9":     [0, 4, 7, 11, 14],# R, M3, P5, M7, M9
    "9":        [0, 4, 7, 10, 14],# R, M3, P5, m7, M9 (Dominant 9th)
    "minor9":   [0, 3, 7, 10, 14],# R, m3, P5, m7, M9
}

# Chord Name Mapping: User Input Alias (lower case) -> Internal Name (key in INTERVALS)
CHORD_TYPE_MAP: Dict[str, str] = {
    # Major-like
    "maj": "major", "major": "major", "": "major", "M": "major", # '' defaults to major
    "maj7": "maj7", "M7": "maj7",
    "maj9": "maj9", "M9": "maj9",
    "6": "6", "maj6": "6", "M6": "6",
    # Minor-like
    "min": "minor", "minor": "minor", "m": "minor", "-": "minor",
    "min7": "minor7", "m7": "minor7", "-7": "minor7",
    "min9": "minor9", "m9": "minor9", "-9": "minor9",
    "min6": "minor6", "m6": "minor6", "-6": "minor6",
    # Dominant-like
    "7": "7", "dom7": "7",
    "9": "9", "dom9": "9",
    # Diminished/Augmented/Suspended
    "dim": "dim", "o": "dim",
    "dim7": "dim7", "o7": "dim7",
    "aug": "aug", "+": "aug",
    "sus4": "sus4", "sus": "sus4",
    "sus2": "sus2",
    "m7b5": "m7b5", "ø": "m7b5", # Half-diminished symbol
}

# Sets for validation, derived from constants
VALID_TYPES: set = set(INTERVALS.keys())
VALID_ROOTS: set = set(CHROMATIC_SCALE)

# --- Helper Functions ---

def sanitize_filename(text: str) -> str:
    """Removes or replaces characters invalid for filenames.

    Args:
        text: The input string (e.g., a plot title or chord name).

    Returns:
        A sanitized string suitable for use in filenames.
    """
    logger.debug(f"Sanitizing: '{text}'")
    text = text.replace("#", "s") # Replace sharp symbol
    text = text.replace("ø", "m7b5") # Replace half-dim symbol if used
    text = text.replace("+", "aug") # Replace + if used
    # Replace spaces, parentheses, and slashes with underscores
    text = re.sub(r"[ \(\)/]+", "_", text)
    # Remove any remaining characters that are not alphanumeric, underscore, or hyphen
    text = re.sub(r"[^a-zA-Z0-9_\-]", "", text)
    # Collapse multiple underscores/hyphens into one
    text = re.sub(r"[_]+", "_", text)
    text = re.sub(r"[-]+", "-", text)
    # Remove leading/trailing underscores/hyphens
    text = text.strip('_-')
    logger.debug(f"Sanitized result: '{text}'")
    return text

def get_chord_notes(root: str, chord_type: str, intervals: List[int]) -> List[str]:
    """Calculates the note names for a chord given root, type, and intervals.

    Args:
        root: The root note (e.g., "C#").
        chord_type: The internal chord type name (e.g., "minor7").
        intervals: The list of semitone intervals for the chord type.

    Returns:
        A list of note names (strings) in the chord.

    Raises:
        ValueError: If the root note is invalid.
        KeyError: If the internal chord_type is not found in INTERVALS.
    """
    if root not in VALID_ROOTS:
        raise ValueError(f"Invalid root note provided: {root}")
    root_index: int = CHROMATIC_SCALE.index(root)
    # Calculate note indices modulo 12 to get the correct note name within the octave
    chord_notes_indices: List[int] = [(root_index + interval) % 12 for interval in intervals]
    return [CHROMATIC_SCALE[note_index] for note_index in chord_notes_indices]

# --- Core Chord Logic ---

def generate_chord_structure(root: str, chord_type: str, inversion: int = 0) -> Tuple[List[str], List[str], str]:
    """Generates the notes, key colors, and title for a specific chord voicing.

    Applies the inversion to the base intervals to determine the actual
    notes being played in the specified inversion.

    Args:
        root: The root note of the chord (e.g., "C", "G#").
        chord_type: The internal type of chord (e.g., "major", "minor7").
        inversion: The inversion number (0 for root position, 1 for first, etc.).

    Returns:
        A tuple containing:
            - list[str]: Note names in the specified inversion.
            - list[str]: Key types ("white" or "black") for each note.
            - str: A title string for the chord diagram (e.g., "C major (Inversion 1)").

    Raises:
        ValueError: If chord_type, root, or inversion number is invalid.
        KeyError: If chord_type is not defined in INTERVALS.
    """
    logger.debug(f"Generating structure: root={root}, type={chord_type}, inv={inversion}")
    if chord_type not in INTERVALS:
        # This should ideally be caught before calling this function
        raise KeyError(f"Internal error: Chord type '{chord_type}' not defined in INTERVALS.")
    if root not in VALID_ROOTS:
         raise ValueError(f"Invalid root note: {root}")

    base_intervals: List[int] = INTERVALS[chord_type][:] # Get a copy
    num_notes: int = len(base_intervals)

    # Validate inversion number
    if not 0 <= inversion < num_notes:
         raise ValueError(f"Inversion {inversion} is invalid for {root} {chord_type} (chord has {num_notes} notes, needs inversion 0-{num_notes-1})")

    # Apply inversion: Rotate intervals and add octaves (12 semitones)
    inverted_intervals: List[int] = base_intervals[:]
    for _ in range(inversion):
        inverted_intervals.append(inverted_intervals.pop(0) + 12)
    # Sort intervals for consistent left-to-right display order in the plot
    inverted_intervals.sort()

    # Calculate note names and key colors based on the *inverted* intervals
    root_index: int = CHROMATIC_SCALE.index(root)
    chord_notes_indices: List[int] = [(root_index + interval) % 12 for interval in inverted_intervals]
    chord_note_names: List[str] = [CHROMATIC_SCALE[idx] for idx in chord_notes_indices]
    key_colors: List[str] = [KEY_TYPES[idx] for idx in chord_notes_indices]

    # Create title string
    inversion_str = f"(Inversion {inversion})" if inversion > 0 else "(Root Position)"
    # Use the internal chord_type name for the title for consistency
    title = f"{root} {chord_type} {inversion_str}"
    logger.debug(f"Generated notes: {chord_note_names}, Title: {title}")

    return chord_note_names, key_colors, title

# --- Chord String Parsing ---

def parse_chord_string(chord_string: str) -> Optional[Tuple[str, str, int]]:
    """Parses a chord string (e.g., 'C#m7', 'G7/B') into (root, type, inversion).

    Args:
        chord_string: The user-provided chord string.

    Returns:
        A tuple (root, internal_chord_type, inversion_number) if parsing is successful,
        otherwise None. Logs warnings/errors on failure.
    """
    logger.debug(f"Attempting to parse: '{chord_string}'")
    original_string = chord_string # Keep for logging
    chord_string = chord_string.strip()

    # Regex: Root note (# optional), then suffix (non-greedy, allows symbols), then optional /Bass note (# optional)
    match = re.match(r"^(?P<root>[A-G]#?)(?P<type>[a-zA-Z0-9\-+oø]*?)(?:/(?P<bass>[A-G]#?))?$", chord_string)

    if not match:
        logger.warning(f"Could not parse chord string structure: '{original_string}'")
        return None

    root: str = match.group("root")
    type_suffix: str = match.group("type")
    bass_note: Optional[str] = match.group("bass")

    # --- Validate Root ---
    if root not in VALID_ROOTS:
        logger.warning(f"Invalid root note '{root}' in string: '{original_string}'")
        return None

    # --- Determine Chord Type (map alias to internal name) ---
    internal_chord_type: Optional[str] = None
    # Handle edge case: only root given (e.g., "C") -> major
    if type_suffix == "" and not bass_note:
         internal_chord_type = "major"
    # Handle root + bass note only (e.g. C/G) -> assumes major chord
    elif type_suffix == "" and bass_note:
         internal_chord_type = "major"
    else:
        # Lookup type suffix in map (case-insensitive)
        internal_chord_type = CHORD_TYPE_MAP.get(type_suffix.lower())

    if internal_chord_type is None:
        logger.warning(f"Unknown chord type suffix '{type_suffix}' in string: '{original_string}'")
        return None

    # Final check: ensure determined type has intervals defined
    if internal_chord_type not in INTERVALS:
        logger.error(f"Internal consistency error: Mapped type '{internal_chord_type}' not found in INTERVALS for string '{original_string}'.")
        return None

    # --- Determine Inversion ---
    inversion: int = 0
    if bass_note:
        if bass_note not in VALID_ROOTS:
            logger.warning(f"Invalid bass note '{bass_note}' in string: '{original_string}'")
            # Decide whether to default to 0 or return None. Defaulting is more forgiving.
            bass_note = None # Ignore invalid bass note, treat as root position
        else:
            # Bass note is valid, try to determine inversion
            try:
                # Get intervals for the *determined* chord type
                root_pos_intervals: List[int] = INTERVALS[internal_chord_type]
                # Get the notes in root position
                root_pos_notes: List[str] = get_chord_notes(root, internal_chord_type, root_pos_intervals)

                # Find the index (0-based) of the bass note in the root position chord
                try:
                    inversion = root_pos_notes.index(bass_note)
                    logger.debug(f"Determined inversion {inversion} from bass note '{bass_note}' for '{original_string}'")
                except ValueError:
                    # Bass note is valid but not naturally in the chord's root position
                    logger.warning(f"Bass note '{bass_note}' not found in root position of '{root} {internal_chord_type}' ({root_pos_notes}). Treating '{original_string}' as root position.")
                    inversion = 0 # Default to root position
            except KeyError:
                 # Should not happen if internal_chord_type check above passed
                 logger.error(f"Internal error finding intervals for '{internal_chord_type}' while checking bass note for '{original_string}'.")
                 return None
            except Exception as e:
                 logger.error(f"Unexpected error determining inversion for '{original_string}': {e}", exc_info=True)
                 return None # Failed unexpectedly

    logger.debug(f"Parsed '{original_string}' as: root={root}, type={internal_chord_type}, inv={inversion}")
    return root, internal_chord_type, inversion


# --- Plotting ---

def plot_chord_diagram(chord_note_names: List[str], key_colors: List[str], title: str) -> plt.Figure:
    """Plots the chord diagram using Matplotlib and NetworkX.

    Args:
        chord_note_names: List of note names in the chord/inversion.
        key_colors: List of "white" or "black" strings for each note.
        title: The title for the plot.

    Returns:
        The matplotlib Figure object containing the plot.
    """
    logger.debug(f"Plotting diagram for: {title}")
    graph = nx.Graph()
    positions = {}
    node_colors_map = []

    # Define node appearance
    node_size = 2500
    font_size = 14
    font_weight = 'bold'

    for i, note in enumerate(chord_note_names):
        # Determine node and text colors based on key type
        key_color_value = (0.2, 0.2, 0.2) if key_colors[i] == "black" else "whitesmoke"
        text_color = "white" if key_colors[i] == "black" else "black"

        # Use unique node IDs internally if the same note appears multiple times (e.g., octaves)
        node_id = f"{note}_{i}"
        graph.add_node(node_id, label=note, color=key_color_value, text_color=text_color)
        node_colors_map.append(key_color_value)

        # Position nodes linearly, slightly raise black keys
        positions[node_id] = (i, 0.1 if key_colors[i] == "black" else 0)

    # Add edges to visually connect adjacent nodes in the plot
    node_ids = list(graph.nodes())
    if len(node_ids) > 1:
        for i in range(len(node_ids) - 1):
            graph.add_edge(node_ids[i], node_ids[i+1])

    # Create a new figure context for each plot to avoid interference
    # Adjust width dynamically based on number of notes for better spacing
    fig_width = max(8, len(chord_note_names) * 1.5 + 1) # Add base width + per node + buffer
    fig = plt.figure(figsize=(fig_width, 4)) # Height fixed at 4

    # Draw the network graph
    nx.draw(
        graph,
        pos=positions,
        with_labels=False, # Labels are drawn manually using plt.text
        node_size=node_size,
        node_color=node_colors_map,
        edge_color="gray",
        width=1.5, # Edge thickness
    )

    # Add note labels manually for better control over appearance
    for node_id, (x, y) in positions.items():
        node_attr = graph.nodes[node_id]
        plt.text(
            x, y, node_attr['label'],
            fontsize=font_size,
            fontweight=font_weight,
            ha="center",        # Horizontal alignment
            va="center",        # Vertical alignment
            color=node_attr['text_color']
        )

    # Add title and adjust layout/axis
    plt.title(title, color="gray", fontsize=20, pad=20) # Add padding above title
    plt.tight_layout() # Adjust plot to prevent labels overlapping borders (before ylim)

    # Adjust y-limits slightly to prevent node clipping
    current_ylim = plt.ylim()
    y_padding = 0.3 # Amount of padding to add above/below
    plt.ylim(current_ylim[0] - y_padding, current_ylim[1] + y_padding)

    plt.axis("off") # Turn off axis lines and ticks

    return fig # Return the figure object


# --- Filename Generation (for PDF base name / Image SubDir name) ---

def generate_output_base_name(args: argparse.Namespace, parser: argparse.ArgumentParser) -> str:
    """Generates a descriptive base filename/subdirectory name based on arguments.

    Args:
        args: The parsed command-line arguments.
        parser: The ArgumentParser instance (to get default values).

    Returns:
        A sanitized base name string.
    """
    if args.chords:
        # Mode 1: Specific Chords
        prefix = "CustomChords"
        # Use first few sanitized original chord strings for the name
        safe_chord_names = [sanitize_filename(c) for c in args.chords[:3]]
        prefix = "-".join(safe_chord_names)
        if len(args.chords) > 3:
            prefix += "_etc"
        return prefix # Already sanitized

    # Mode 2: Combination Mode
    # Compare provided args against the defaults set in the parser
    default_roots = parser.get_default("roots")
    default_types_input = parser.get_default("types") # User input types default
    default_inversions = parser.get_default("inversions")

    # Roots part
    if set(args.roots) == set(default_roots):
        roots_part = "Roots_All"
    elif len(args.roots) == 1:
        roots_part = f"Root_{args.roots[0]}"
    else:
        # Limit length if many specific roots are given
        roots_str = "-".join(args.roots)
        roots_part = f"Roots_{len(args.roots)}Custom" if len(roots_str) > 20 else f"Roots_{roots_str}"

    # Types part - Compare against user *input* default list
    if set(args.types) == set(default_types_input):
        types_part = "Types_All"
    elif len(args.types) == 1:
         # Use the user's input name if only one type provided
        types_part = f"Type_{args.types[0]}"
    else:
        types_str = "-".join(args.types)
        types_part = f"Types_{len(args.types)}Custom" if len(types_str) > 20 else f"Types_{types_str}"

    # Inversions part
    # Describe the requested range, not necessarily the valid ones per chord
    if set(args.inversions) == set(default_inversions):
        inversions_part = "Invs_Default"
    else:
        requested_invs_str = "-".join(map(str, sorted(list(set(args.inversions)))))
        inversions_part = f"Invs_{requested_invs_str}"

    if args.skip_root:
        inversions_part += "_NoRootPos"

    # Combine and sanitize the final base name
    base_filename = f"{roots_part}_{types_part}_{inversions_part}"
    return sanitize_filename(base_filename)

# --- Main Execution ---

def main():
    """Parses arguments, determines chords, generates diagrams, and saves output."""
    parser = argparse.ArgumentParser(
        description="Generate musical chord diagrams as PDF or individual image files (PNG/JPG).\n"
                    "Provide EITHER specific chords via --chords OR use combination flags (-r, -t, -i).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Show default values in help message
    )

    # --- Argument Groups for Clarity ---
    input_mode_group = parser.add_mutually_exclusive_group(required=False)
    input_mode_group.add_argument("-c", "--chords", nargs='+',
                             help="List of specific chord strings (e.g., 'Cmaj7' 'G7/B' 'Am'). Overrides combination flags.")

    combo_group = parser.add_argument_group('Combination Mode Options (used if --chords is not specified)')
    # Use the constants for defaults where appropriate
    combo_group.add_argument("-r", "--roots", nargs='+', default=CHROMATIC_SCALE, help="List of root notes.")
    # Default to a smaller, common set of types for the help message, but process all if user provides them
    combo_group.add_argument("-t", "--types", nargs='+', default=["major", "minor", "7", "m7", "maj7"], help="List of chord types/aliases.")
    combo_group.add_argument("-i", "--inversions", type=int, nargs='+', default=[0, 1, 2, 3], help="List of inversion numbers (max depends on chord).")
    combo_group.add_argument("--skip-root", action='store_true', help="Skip root position chords (Inversion 0).")

    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument("--format", choices=['pdf', 'png', 'jpg'], default='pdf', help="Output file format.")
    output_group.add_argument("--output-dir", default='./chord_graphs', help="Directory to save output file(s). Image formats will be saved in a subdirectory within this directory.")

    args = parser.parse_args()

    # --- Determine Chords to Generate ---
    chords_to_process: List[Tuple[str, str, int]] = [] # Store as (root, internal_type, inversion)

    if args.chords:
        # Mode 1: Specific Chords Provided
        logger.info(f"Processing specific chords: {', '.join(args.chords)}")
        for chord_str in args.chords:
            parsed = parse_chord_string(chord_str)
            if parsed:
                chords_to_process.append(parsed)
            else:
                logger.warning(f"Skipping unparseable or invalid chord: '{chord_str}'")
    else:
        # Mode 2: Combination Mode (using -r, -t, -i flags)
        logger.info("Using combination mode to generate chords.")

        # Map user-provided type names/aliases to internal types
        mapped_types = set() # Use set to store unique internal types
        valid_input_types = [] # Keep track of valid user input for logging
        invalid_input_types = []
        for t_input in args.types:
            internal_type = CHORD_TYPE_MAP.get(t_input.lower())
            if internal_type and internal_type in VALID_TYPES:
                mapped_types.add(internal_type)
                if t_input not in valid_input_types: # Avoid logging duplicates if user enters 'm' and 'minor'
                     valid_input_types.append(t_input)
            else:
                invalid_input_types.append(t_input)

        if invalid_input_types:
            logger.warning(f"Ignoring unknown or unsupported chord types: {', '.join(invalid_input_types)}")

        # Use the unique set of successfully mapped internal types
        requested_internal_types = sorted(list(mapped_types))

        # Filter valid roots
        requested_roots = [r for r in args.roots if r in VALID_ROOTS]
        invalid_roots = [r for r in args.roots if r not in VALID_ROOTS]
        if invalid_roots:
            logger.warning(f"Ignoring invalid root notes: {', '.join(invalid_roots)}")

        # Check if there's anything valid left to generate
        if not requested_roots or not requested_internal_types:
            logger.error("No valid roots or types specified for combination mode. Exiting.")
            return

        # Log the effective parameters being used
        # Check if default lists were used for roots/types for concise logging
        roots_to_log = requested_roots if set(requested_roots) != set(parser.get_default("roots")) else ['All Defaults']
        types_to_log = valid_input_types if set(valid_input_types) != set(parser.get_default("types")) else ['All Defaults']
        logger.info(f"Generating combinations for roots: {', '.join(roots_to_log)}")
        logger.info(f"Using chord types (input aliases): {', '.join(types_to_log)}")
        logger.info(f"Requested inversions: {', '.join(map(str, sorted(list(set(args.inversions)))))}")


        # Generate the list of (root, type, inversion) tuples
        for root in requested_roots:
            for chord_type in requested_internal_types: # Iterate using internal types
                try:
                    num_notes = len(INTERVALS[chord_type])
                    # Filter requested inversions based on validity for this specific chord
                    valid_inversions = [inv for inv in args.inversions if 0 <= inv < num_notes]
                    # Apply skip_root logic
                    if args.skip_root and 0 in valid_inversions:
                         valid_inversions.remove(0)
                    # Process unique valid inversions
                    active_inversions = sorted(list(set(valid_inversions)))
                    for inversion in active_inversions:
                        chords_to_process.append((root, chord_type, inversion))
                except KeyError:
                     # Should not happen if VALID_TYPES is correct, but safeguard
                     logger.error(f"Internal error: No intervals defined for type '{chord_type}'. Skipping combination.")
                     continue

    # Check if any chords were successfully identified/generated
    if not chords_to_process:
        logger.error("No valid chords identified or generated based on input. Exiting.")
        return

    # --- Prepare Base Output Directory ---
    try:
        # Create the main output directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)
        logger.info(f"Using base output directory: {args.output_dir}")
    except OSError as e:
        logger.error(f"Could not create base output directory '{args.output_dir}': {e}")
        return

    # --- Generate and Save Output ---
    count = 0
    # Generate the base name for PDF filename or image subdirectory name
    output_base_name = generate_output_base_name(args, parser) # Pass parser to access defaults

    if args.format == 'pdf':
        # --- PDF Output ---
        pdf_filepath = os.path.join(args.output_dir, f"{output_base_name}.pdf")
        logger.info(f"Generating PDF: {pdf_filepath}")
        try:
            with PdfPages(pdf_filepath) as pdf:
                for root, chord_type, inversion in chords_to_process:
                    try:
                        notes, keys, title = generate_chord_structure(root, chord_type, inversion)
                        fig = plot_chord_diagram(notes, keys, title) # Generate plot figure
                        pdf.savefig(fig, bbox_inches="tight") # Save figure to PDF page
                        plt.close(fig) # Close the figure to free memory
                        count += 1
                        logger.debug(f"Added diagram to PDF: {title}")
                    except ValueError as e: # Catch errors from generate_chord_structure or plotting
                        logger.error(f"Skipping chord {root} {chord_type} inv{inversion} for PDF due to error: {e}")
                    except Exception as e: # Catch unexpected errors
                        logger.error(f"Unexpected error generating PDF page for {root} {chord_type} inv{inversion}: {e}", exc_info=True)
                logger.info(f"Successfully added {count} diagrams to PDF.")
        except Exception as e:
             # Error opening/writing the PDF file itself
             logger.error(f"Failed to open or write PDF file '{pdf_filepath}': {e}", exc_info=True)
             return

    else:
        # --- Image Output (PNG/JPG) ---
        # Create a subdirectory named using the generated base name
        image_subdir = os.path.join(args.output_dir, output_base_name)
        try:
            os.makedirs(image_subdir, exist_ok=True)
            logger.info(f"Generating individual {args.format.upper()} files in subdirectory: {image_subdir}")
        except OSError as e:
            logger.error(f"Could not create image subdirectory '{image_subdir}': {e}")
            return # Cannot proceed if subdirectory creation fails

        for root, chord_type, inversion in chords_to_process:
             try:
                notes, keys, title = generate_chord_structure(root, chord_type, inversion)
                fig = plot_chord_diagram(notes, keys, title) # Generate plot figure

                # Create individual filename based on the diagram's title
                img_filename = sanitize_filename(title) + f".{args.format}"
                img_filepath = os.path.join(image_subdir, img_filename) # Full path

                # Save the figure directly as an image file
                fig.savefig(img_filepath, format=args.format, bbox_inches="tight", dpi=150) # Optional: set dpi
                plt.close(fig) # Close the figure to free memory
                count += 1
                logger.debug(f"Saved image: {img_filepath}")
             except ValueError as e: # Catch errors from generate_chord_structure or plotting
                 logger.error(f"Skipping image for chord {root} {chord_type} inv{inversion} due to error: {e}")
             except Exception as e: # Catch unexpected errors during saving etc.
                 logger.error(f"Unexpected error generating image for {root} {chord_type} inv{inversion}: {e}", exc_info=True)

    # --- Final Log Message ---
    if count > 0:
        # Construct the final location description based on format
        if args.format == 'pdf':
            final_path = os.path.join(args.output_dir, f"{output_base_name}.pdf")
            final_location_desc = f"PDF file '{final_path}'"
        else:
            final_path = os.path.join(args.output_dir, output_base_name)
            final_location_desc = f"subdirectory '{final_path}'"

        logger.info(f"Finished! Generated {count} diagram(s) as {args.format.upper()} in {final_location_desc}.")
    else:
        logger.warning("Finished, but no diagrams were generated due to errors or invalid input.")


if __name__ == "__main__":
    main()