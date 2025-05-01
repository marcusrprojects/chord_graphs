# chord_generator.py

import itertools
import argparse
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.backends.backend_pdf import PdfPages
import logging
import re
import os
from typing import List, Tuple, Optional, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants ---
CHROMATIC_SCALE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
KEY_TYPES = ["white", "black", "white", "black", "white", "white", "black", "white", "black", "white", "black", "white"]

INTERVALS = {
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
    "m7b5":     [0, 3, 6, 10],   # R, m3, d5, m7 (Half-diminished 7th) - Added common name/chord
    # Sixths
    "6":        [0, 4, 7, 9],    # R, M3, P5, M6 (Major 6th)
    "minor6":   [0, 3, 7, 9],    # R, m3, P5, M6 (Minor 6th) - Note: M6 added to minor triad
    # Ninths (Based on adding M9 (14) to 7th chords)
    "maj9":     [0, 4, 7, 11, 14],# R, M3, P5, M7, M9
    "9":        [0, 4, 7, 10, 14],# R, M3, P5, m7, M9 (Dominant 9th)
    "minor9":   [0, 3, 7, 10, 14],# R, m3, P5, m7, M9
}

CHORD_TYPE_MAP = {
    # Major-like
    "maj": "major", "major": "major", "": "major", "M": "major",
    "maj7": "maj7", "M7": "maj7",
    "maj9": "maj9", "M9": "maj9",
    "6": "6", "maj6": "6", "M6":"6",
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
    "sus4": "sus4", "sus": "sus4", # Common short version
    "sus2": "sus2",
    "m7b5": "m7b5", "ø": "m7b5", # Half-diminished symbol
}

# Update Valid Types Set automatically from INTERVALS keys
VALID_TYPES = set(INTERVALS.keys())
VALID_ROOTS = set(CHROMATIC_SCALE)

# --- Helper Functions ---
def sanitize_filename(text: str) -> str:
    text = text.replace("#", "s")
    # Handle ø symbol if present in titles derived from input
    text = text.replace("ø", "m7b5")
    text = re.sub(r"[ \(\)]+", "_", text)
    text = re.sub(r"[^a-zA-Z0-9_\-]", "", text)
    text = re.sub(r"_+", "_", text)
    text = text.strip('_')
    return text

def get_chord_notes(root: str, chord_type: str, intervals: List[int]) -> List[str]:
    root_index = CHROMATIC_SCALE.index(root)
    chord_notes_indices = [(root_index + interval) % 12 for interval in intervals]
    return [CHROMATIC_SCALE[note_index] for note_index in chord_notes_indices]

# --- Core Chord Logic ---
def generate_chord_structure(root: str, chord_type: str, inversion: int = 0) -> Tuple[List[str], List[str], str]:
    if chord_type not in INTERVALS:
        raise ValueError(f"Internal error: Unsupported chord type '{chord_type}' used.") # Should be caught earlier
    if root not in VALID_ROOTS:
         raise ValueError(f"Invalid root note: {root}")
    chord_intervals = INTERVALS[chord_type][:]
    num_notes = len(chord_intervals)
    if inversion >= num_notes:
         # Modify error message slightly for clarity
         raise ValueError(f"Inversion {inversion} is invalid for {root} {chord_type} (needs 0-{num_notes-1})")
    actual_inversion = inversion
    temp_intervals = chord_intervals[:]
    for _ in range(actual_inversion):
        temp_intervals.append(temp_intervals.pop(0) + 12)
    temp_intervals.sort()
    root_index = CHROMATIC_SCALE.index(root)
    chord_notes_indices = [(root_index + interval) % 12 for interval in temp_intervals]
    chord_note_names = [CHROMATIC_SCALE[note_index] for note_index in chord_notes_indices]
    key_colors = [KEY_TYPES[note_index] for note_index in chord_notes_indices]
    inversion_str = f"(Inversion {actual_inversion})" if actual_inversion > 0 else "(Root Position)"
    # Use the potentially mapped type name for the title if different from internal key
    display_type = chord_type
    title = f"{root} {display_type} {inversion_str}"
    return chord_note_names, key_colors, title

# --- Chord String Parsing ---
def parse_chord_string(chord_string: str) -> Optional[Tuple[str, str, int]]:
    """
    Parses a chord string. Handles more types now.
    Regex improved slightly to better handle suffixes like m7b5, aug, etc.
    It looks for Root -> Suffix -> Optional /Bass
    """
    # Regex: Root note (# optional), then suffix (non-greedy, allows symbols), then optional /Bass note (# optional)
    # Allow '-', '+', 'ø', 'o' in the type suffix now. Adjusted suffix pattern.
    # Suffix can be letters, numbers, -, +, o, ø. '*' allows zero or more.
    match = re.match(r"^(?P<root>[A-G]#?)(?P<type>[a-zA-Z0-9\-+oø]*?)(?:/(?P<bass>[A-G]#?))?$", chord_string.strip())

    if not match:
        logging.warning(f"Could not parse chord string structure: '{chord_string}'")
        return None

    root = match.group("root")
    type_suffix = match.group("type")
    bass_note = match.group("bass")

    if root not in VALID_ROOTS:
        logging.warning(f"Invalid root note '{root}' in string: '{chord_string}'")
        return None

    # Handle edge case: only root given (e.g., "C") -> major
    if type_suffix == "" and not bass_note:
         chord_type = "major"
    # Handle root + bass note only (e.g. C/G) -> major chord with inversion
    elif type_suffix == "" and bass_note:
         chord_type = "major"
    else:
        # Lookup type suffix in map
        chord_type = CHORD_TYPE_MAP.get(type_suffix.lower()) # Use lower for case-insensitivity

    if chord_type is None:
        # Maybe try without lower if map contains case-sensitive keys? No, stick to lower.
        logging.warning(f"Unknown chord type suffix '{type_suffix}' in string: '{chord_string}'")
        return None

    # Determine inversion
    inversion = 0
    if bass_note:
        if bass_note not in VALID_ROOTS:
            logging.warning(f"Invalid bass note '{bass_note}' in string: '{chord_string}'")
            return None
        try:
            root_pos_intervals = INTERVALS[chord_type]
            root_pos_notes = get_chord_notes(root, chord_type, root_pos_intervals)
            try:
                inversion = root_pos_notes.index(bass_note)
            except ValueError:
                logging.warning(f"Bass note '{bass_note}' not found in root position of '{root} {chord_type}'. Cannot determine inversion for '{chord_string}'. Treating as root position.")
                inversion = 0
        except KeyError:
             logging.error(f"Internal error: Could not find intervals for parsed type '{chord_type}' while checking bass note for '{chord_string}'.")
             return None
        except Exception as e:
             logging.error(f"Error determining inversion for '{chord_string}': {e}")
             return None

    # Final check: ensure determined type has intervals defined
    if chord_type not in INTERVALS:
        logging.error(f"Internal consistency error: Mapped type '{chord_type}' not found in INTERVALS for string '{chord_string}'.")
        return None

    return root, chord_type, inversion


# --- Plotting ---
def plot_chord_diagram(chord_note_names, key_colors, title):
    graph = nx.Graph()
    positions = {}
    node_colors_map = []
    for i, note in enumerate(chord_note_names):
        key_color_value = (.2, .2, .2) if key_colors[i] == "black" else "whitesmoke"
        text_color = "white" if key_colors[i] == "black" else "black"
        node_id = f"{note}_{i}"
        graph.add_node(node_id, label=note, color=key_color_value, text_color=text_color)
        node_colors_map.append(key_color_value)
        positions[node_id] = (i, 0.1 if key_colors[i] == "black" else 0)
    node_ids = list(graph.nodes())
    for i in range(len(node_ids) - 1):
        graph.add_edge(node_ids[i], node_ids[i+1])
    fig = plt.figure(figsize=(max(8, len(chord_note_names)*1.5), 4))
    nx.draw(
        graph, pos=positions, with_labels=False, node_size=2500,
        node_color=node_colors_map, edge_color="gray", width=1.5,
    )
    for node_id, (x, y) in positions.items():
        node_attr = graph.nodes[node_id]
        plt.text(
            x, y, node_attr['label'], fontsize=14, fontweight='bold',
            ha="center", va="center", color=node_attr['text_color']
        )
    plt.title(title, color="gray", fontsize=20, pad=20)
    plt.tight_layout()
    current_ylim = plt.ylim()
    plt.ylim(current_ylim[0] - 0.3, current_ylim[1] + 0.3)
    plt.axis("off")
    return fig

# --- Filename Generation ---
def generate_output_base_name(args):
    if args.chords:
        prefix = "CustomChords"
        if args.chords:
            safe_chord_names = [sanitize_filename(c) for c in args.chords[:3]]
            prefix = "-".join(safe_chord_names)
            if len(args.chords) > 3:
                prefix += "_etc"
        return prefix
    default_roots = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    # Use updated VALID_TYPES derived from INTERVALS keys for comparison
    default_types = list(VALID_TYPES) # Get all currently supported types
    roots_part = "Roots_All" if set(args.roots) == set(default_roots) else \
                 f"Root_{args.roots[0]}" if len(args.roots) == 1 else \
                 f"Roots_{len(args.roots)}Custom" if len("-".join(args.roots)) > 20 else \
                 f"Roots_{'-'.join(args.roots)}"
    types_part = "Types_All" if set(args.types) == set(default_types) else \
                 f"Type_{args.types[0]}" if len(args.types) == 1 else \
                 f"Types_{len(args.types)}Custom" if len("-".join(args.types)) > 20 else \
                 f"Types_{'-'.join(args.types)}"
    requested_invs_str = "-".join(map(str, sorted(list(set(args.inversions)))))
    inversions_part = f"Invs_{requested_invs_str}"
    if args.skip_root:
        inversions_part += "_NoRootPos"
    base_filename = f"{roots_part}_{types_part}_{inversions_part}"
    return sanitize_filename(base_filename)


# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(
        description="Generate musical chord diagrams. Provide EITHER --chords OR combination flags (-r, -t, -i).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("-c", "--chords", nargs='+',
                             help="List of specific chord strings (e.g., 'Cmaj7' 'G7/B' 'Am' 'Fsus4' 'Bdim7').")
    # Update help text for types to reflect new additions
    parser.add_argument("-r", "--roots", nargs='+', default=CHROMATIC_SCALE, help="List of root notes for combination mode.")
    parser.add_argument("-t", "--types", nargs='+', default=list(VALID_TYPES), help="List of chord types for combination mode.")
    parser.add_argument("-i", "--inversions", type=int, nargs='+', default=[0, 1, 2, 3], help="List of inversion numbers (max depends on chord).") # Adjusted help
    parser.add_argument("--skip-root", action='store_true', help="Skip root position in combination mode.")
    parser.add_argument("--format", choices=['pdf', 'png', 'jpg'], default='pdf', help="Output format.")
    parser.add_argument("--output-dir", default='./chord_graphs', help="Base directory to save output file(s) or image subdirectory.")

    args = parser.parse_args()

    # --- Determine chords to generate ---
    chords_to_process: List[Tuple[str, str, int]] = []

    if args.chords:
        # Specific Chords Mode
        logging.info(f"Processing specific chords: {', '.join(args.chords)}")
        for chord_str in args.chords:
            parsed = parse_chord_string(chord_str)
            if parsed:
                chords_to_process.append(parsed)
            else:
                logging.warning(f"Skipping unparseable or invalid chord: '{chord_str}'") # Adjusted message
    else:
        # Combination Mode
        # Map user-provided types (which might be aliases) to internal types
        mapped_types = []
        valid_input_types = []
        invalid_input_types = []
        for t in args.types:
            internal_type = CHORD_TYPE_MAP.get(t.lower())
            if internal_type and internal_type in VALID_TYPES:
                mapped_types.append(internal_type)
                valid_input_types.append(t) # Keep track of valid user input
            else:
                invalid_input_types.append(t)

        if invalid_input_types:
            logging.warning(f"Ignoring unknown or unsupported chord types: {', '.join(invalid_input_types)}")

        # Use the unique set of successfully mapped internal types
        requested_types = sorted(list(set(mapped_types)))

        # Filter roots
        requested_roots = [r for r in args.roots if r in VALID_ROOTS]
        invalid_roots = [r for r in args.roots if r not in VALID_ROOTS]
        if invalid_roots:
            logging.warning(f"Ignoring invalid root notes: {', '.join(invalid_roots)}")

        if not requested_roots or not requested_types:
            logging.error("No valid roots or types available for combination mode. Exiting.")
            return

        # Logging using valid *input* types for clarity if possible
        roots_to_log = requested_roots if len(requested_roots) < len(VALID_ROOTS) else ['All Defaults']
        types_to_log = valid_input_types if len(valid_input_types) < len(VALID_TYPES) else ['All Defaults']
        logging.info(f"Generating combinations for roots: {', '.join(roots_to_log)}")
        logging.info(f"Chord types (internal): {', '.join(requested_types)}") # Log internal types being used
        logging.info(f"Requested inversions: {', '.join(map(str, sorted(list(set(args.inversions)))))}")


        for root in requested_roots:
            for chord_type in requested_types: # Iterate through internal types
                try:
                    num_notes = len(INTERVALS[chord_type])
                    valid_requested_inversions = [inv for inv in args.inversions if 0 <= inv < num_notes]
                    if args.skip_root and 0 in valid_requested_inversions:
                         valid_requested_inversions.remove(0)
                    active_inversions = sorted(list(set(valid_requested_inversions)))
                    for inversion in active_inversions:
                        chords_to_process.append((root, chord_type, inversion))
                except KeyError:
                     logging.error(f"Internal error: No intervals defined for type '{chord_type}'. Skipping.")
                     continue # Skip this type if intervals somehow missing


    if not chords_to_process:
        logging.error("No valid chords to generate. Exiting.")
        return

    # --- Prepare Base Output Directory ---
    try:
        os.makedirs(args.output_dir, exist_ok=True)
        logging.info(f"Using base output directory: {args.output_dir}")
    except OSError as e:
        logging.error(f"Could not create base output directory '{args.output_dir}': {e}")
        return

    # --- Generate and Save Output ---
    count = 0
    output_base_name = generate_output_base_name(args)

    if args.format == 'pdf':
        pdf_filepath = os.path.join(args.output_dir, f"{output_base_name}.pdf")
        logging.info(f"Generating PDF: {pdf_filepath}")
        try:
            with PdfPages(pdf_filepath) as pdf:
                for root, chord_type, inversion in chords_to_process:
                    try:
                        notes, keys, title = generate_chord_structure(root, chord_type, inversion)
                        fig = plot_chord_diagram(notes, keys, title)
                        pdf.savefig(fig, bbox_inches="tight")
                        plt.close(fig)
                        count += 1
                        logging.info(f"Added diagram to PDF: {title}")
                    except ValueError as e: logging.error(f"Skipping chord {root} {chord_type} inv{inversion} for PDF: {e}")
                    except Exception as e: logging.error(f"Unexpected PDF generation error for {root} {chord_type} inv{inversion}: {e}", exc_info=True)
        except Exception as e:
             logging.error(f"Failed to open or write PDF file '{pdf_filepath}': {e}")
             return

    else: # Image Mode (PNG/JPG)
        image_subdir = os.path.join(args.output_dir, output_base_name)
        try:
            os.makedirs(image_subdir, exist_ok=True)
            logging.info(f"Generating individual {args.format.upper()} files in subdirectory: {image_subdir}")
        except OSError as e:
            logging.error(f"Could not create image subdirectory '{image_subdir}': {e}")
            return

        for root, chord_type, inversion in chords_to_process:
             try:
                notes, keys, title = generate_chord_structure(root, chord_type, inversion)
                fig = plot_chord_diagram(notes, keys, title)
                img_filename = sanitize_filename(title) + f".{args.format}"
                img_filepath = os.path.join(image_subdir, img_filename)
                fig.savefig(img_filepath, format=args.format, bbox_inches="tight")
                plt.close(fig)
                count += 1
                logging.info(f"Saved image: {img_filepath}")
             except ValueError as e: logging.error(f"Skipping image for chord {root} {chord_type} inv{inversion}: {e}")
             except Exception as e: logging.error(f"Unexpected image generation error for {root} {chord_type} inv{inversion}: {e}", exc_info=True)


    # --- Final Log Message ---
    final_location = f"file '{os.path.join(args.output_dir, f'{output_base_name}.pdf')}'" if args.format == 'pdf' \
                else f"subdirectory '{os.path.join(args.output_dir, output_base_name)}'"
    logging.info(f"Finished! Generated {count} diagram(s) as {args.format.upper()} in {final_location}.")


if __name__ == "__main__":
    main()