# chord_generator.py

import itertools
import argparse
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.backends.backend_pdf import PdfPages
import logging
import re
from typing import List, Tuple, Optional, Dict # For type hinting

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants ---
CHROMATIC_SCALE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
KEY_TYPES = ["white", "black", "white", "black", "white", "white", "black", "white", "black", "white", "black", "white"]
INTERVALS = {
    "major": [0, 4, 7],
    "minor": [0, 3, 7],
    "7": [0, 4, 7, 10],
    "minor7": [0, 3, 7, 10],
    "maj7": [0, 4, 7, 11],
}
# Map common names/symbols to internal types
CHORD_TYPE_MAP = {
    "maj": "major", "major": "major", "": "major", "M": "major", # '' assumes major if only root is given
    "min": "minor", "minor": "minor", "m": "minor", "-": "minor",
    "7": "7", "dom7": "7",
    "m7": "minor7", "min7": "minor7", "-7": "minor7",
    "maj7": "maj7", "M7": "maj7",
}
VALID_TYPES = set(INTERVALS.keys())
VALID_ROOTS = set(CHROMATIC_SCALE)

# --- Core Chord Logic ---

def get_chord_notes(root: str, chord_type: str, intervals: List[int]) -> List[str]:
    """Calculates the note names for a chord given intervals (helper function)."""
    root_index = CHROMATIC_SCALE.index(root)
    chord_notes_indices = [(root_index + interval) % 12 for interval in intervals]
    return [CHROMATIC_SCALE[note_index] for note_index in chord_notes_indices]

def generate_chord_structure(root: str, chord_type: str, inversion: int = 0) -> Tuple[List[str], List[str], str]:
    """
    Generates the notes and structure for a given musical chord.
    Args, Returns, Raises documented as before.
    """
    if chord_type not in INTERVALS:
        raise ValueError(f"Unsupported chord type: {chord_type}")
    if root not in VALID_ROOTS:
         raise ValueError(f"Invalid root note: {root}")

    chord_intervals = INTERVALS[chord_type][:] # Make a copy

    num_notes = len(chord_intervals)
    if inversion >= num_notes:
         raise ValueError(f"Inversion {inversion} is invalid for a {num_notes}-note chord ({root} {chord_type})")

    actual_inversion = inversion

    # Apply inversion by rotating intervals and adding octaves
    temp_intervals = chord_intervals[:]
    for _ in range(actual_inversion):
        temp_intervals.append(temp_intervals.pop(0) + 12)
    temp_intervals.sort() # Keep intervals sorted for consistent note order display

    # Calculate note names based on inverted intervals
    root_index = CHROMATIC_SCALE.index(root)
    chord_notes_indices = [(root_index + interval) % 12 for interval in temp_intervals]
    chord_note_names = [CHROMATIC_SCALE[note_index] for note_index in chord_notes_indices]
    key_colors = [KEY_TYPES[note_index] for note_index in chord_notes_indices]

    inversion_str = f"(Inversion {actual_inversion})" if actual_inversion > 0 else "(Root Position)"
    # Adjust title slightly for clarity if specific bass note was used for inversion
    title = f"{root} {chord_type} {inversion_str}" # Keep it simple for now

    return chord_note_names, key_colors, title

def parse_chord_string(chord_string: str) -> Optional[Tuple[str, str, int]]:
    """
    Parses a chord string like 'C#m7', 'G7/B' into (root, type, inversion).
    Returns None if parsing fails.
    """
    # Regex to capture root, type suffix, and optional /bassnote
    # Root: (C|D|E|F|G|A|B)(#|b)?
    # Type: (\w*?)?? - Non-greedy match for type suffix
    # Bass: (?:/(C|D|E|F|G|A|B)(#|b)?)? - Optional non-capturing group for / and bass note
    match = re.match(r"^(?P<root>[A-G]#?)(?P<type>\w*?|)(?:/(?P<bass>[A-G]#?))?$", chord_string.strip())

    if not match:
        logging.warning(f"Could not parse chord string: '{chord_string}'")
        return None

    root = match.group("root")
    type_suffix = match.group("type")
    bass_note = match.group("bass")

    # Normalize root note (we internally only use sharps)
    # Add more normalization if needed (e.g., Db -> C#) - keeping simple for now
    if root not in VALID_ROOTS:
        logging.warning(f"Invalid root note '{root}' in string: '{chord_string}'")
        return None

    # Determine chord type
    chord_type = CHORD_TYPE_MAP.get(type_suffix.lower())
    if chord_type is None:
        logging.warning(f"Unknown chord type suffix '{type_suffix}' in string: '{chord_string}'")
        return None

    # Determine inversion
    inversion = 0
    if bass_note:
        if bass_note not in VALID_ROOTS:
            logging.warning(f"Invalid bass note '{bass_note}' in string: '{chord_string}'")
            return None
        try:
            # Get root position notes to find inversion
            root_pos_intervals = INTERVALS[chord_type]
            root_pos_notes = get_chord_notes(root, chord_type, root_pos_intervals)
            
            # Find the index of the bass note in the root position chord
            try:
                inversion = root_pos_notes.index(bass_note)
            except ValueError:
                logging.warning(f"Bass note '{bass_note}' not found in root position of '{root} {chord_type}'. Cannot determine inversion for '{chord_string}'. Treating as root position.")
                inversion = 0 # Default to root if bass note doesn't fit simple inversion

        except Exception as e:
             logging.error(f"Error determining inversion for '{chord_string}': {e}")
             return None # Failed to determine inversion

    return root, chord_type, inversion


def plot_chord_diagram(chord_note_names, key_colors, title):
    """
    Plots the chord diagram using Matplotlib and NetworkX.

    Args:
        chord_note_names (list[str]): Names of the notes in the chord.
        key_colors (list[str]): Key types ("white" or "black") for each note.
        title (str): The title for the plot.
    """
    graph = nx.Graph()
    positions = {}
    node_colors_map = []

    for i, note in enumerate(chord_note_names):
        key_color_value = (.2, .2, .2) if key_colors[i] == "black" else "whitesmoke"
        text_color = "white" if key_colors[i] == "black" else "black"
        # Ensure unique node names if duplicates exist (e.g., in inversions)
        node_id = f"{note}_{i}"
        graph.add_node(node_id, label=note, color=key_color_value, text_color=text_color)
        node_colors_map.append(key_color_value)
        # Position black keys slightly higher
        positions[node_id] = (i, 0.1 if key_colors[i] == "black" else 0)

    # Connect the notes (visually, not necessarily musically adjacent)
    node_ids = list(graph.nodes())
    for i in range(len(node_ids) - 1):
        graph.add_edge(node_ids[i], node_ids[i+1])

    # Create a new figure for each plot
    plt.figure(figsize=(8, 4)) # Adjusted figure size
    nx.draw(
        graph,
        pos=positions,
        with_labels=False,
        node_size=2500,
        node_color=node_colors_map,
        edge_color="gray",
        width=1.5,
    )

    # Add labels with appropriate text colors
    for node_id, (x, y) in positions.items():
        node_attr = graph.nodes[node_id]
        plt.text(
            x, y, node_attr['label'],
            fontsize=14,
            fontweight='bold',
            ha="center",
            va="center",
            color=node_attr['text_color']
        )

    plt.title(title, color="gray", fontsize=20, pad=20)
    plt.tight_layout()

    current_ylim = plt.ylim()
    # Add a buffer to the top and bottom limits
    plt.ylim(current_ylim[0] - 0.1, current_ylim[1] + 0.1)
    plt.axis("off") # Turn off axis AFTER adjusting limits

def generate_filename(args):
    """Generates a descriptive filename based on arguments."""

    # If specific chords are given, use a simpler naming scheme
    if args.chords:
         # Use first few chords if possible, sanitize
        prefix = "CustomChords"
        if args.chords:
            safe_chord_names = [re.sub(r'[\\/*?:"<>|#]', "", c.replace("#", "s")) for c in args.chords[:3]]
            prefix = "-".join(safe_chord_names)
            if len(args.chords) > 3:
                prefix += "_etc"
        return f"{prefix}.pdf"

    default_roots = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    default_types = ["major", "minor", "7", "minor7", "maj7"]

    # Roots part
    if set(args.roots) == set(default_roots):
        roots_part = "Roots_All"
    elif len(args.roots) == 1:
        roots_part = f"Root_{args.roots[0]}"
    else:
        roots_str = "-".join(args.roots)
        roots_part = f"Roots_{len(args.roots)}Custom" if len(roots_str) > 20 else f"Roots_{roots_str}"

    # Types part
    if set(args.types) == set(default_types):
        types_part = "Types_All"
    elif len(args.types) == 1:
        types_part = f"Type_{args.types[0]}"
    else:
        types_str = "-".join(args.types)
        types_part = f"Types_{len(args.types)}Custom" if len(types_str) > 20 else f"Types_{types_str}"

    # Inversions part
    requested_invs_str = "-".join(map(str, sorted(list(set(args.inversions)))))
    inversions_part = f"Invs_{requested_invs_str}"
    if args.skip_root:
        inversions_part += "_NoRootPos"

    base_filename = f"{roots_part}_{types_part}_{inversions_part}"
    sanitized_filename = base_filename.replace("#", "s")
    sanitized_filename = re.sub(r'[\\/*?:"<>|]', "", sanitized_filename)

    return f"{sanitized_filename}.pdf"


# --- Main Execution ---
def main():
    """Main function to parse arguments and generate chord diagrams."""
    parser = argparse.ArgumentParser(description="Generate musical chord diagrams and save them to PDF. Provide EITHER --chords OR combination flags (-r, -t, -i).")

    # Mode 1: Specific Chords
    parser.add_argument("-c", "--chords", nargs='+', default=None,
                        help="List of specific chord strings to generate (e.g., 'Cmaj7' 'G7/B' 'Am'). Conflicts with -r, -t, -i.")

    # Mode 2: Combinations
    parser.add_argument("-r", "--roots", nargs='+', default=["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"],
                        help="List of root notes (Conflicts with --chords).")
    parser.add_argument("-t", "--types", nargs='+', default=["major", "minor", "7", "minor7", "maj7"],
                        help="List of chord types (Conflicts with --chords).")
    parser.add_argument("-i", "--inversions", type=int, nargs='+', default=[0, 1, 2, 3],
                        help="List of inversion numbers (Conflicts with --chords).")
    parser.add_argument("--skip-root", action='store_true',
                        help="Skip root position in combination mode (Conflicts with --chords).")

    # Output file - works for both modes
    parser.add_argument("-o", "--output", default=None,
                        help="Output PDF filename. If omitted, a descriptive name is generated automatically.")

    args = parser.parse_args()

    # --- Validate argument usage ---
    combination_mode_args = args.roots != parser.get_default("roots") or \
                            args.types != parser.get_default("types") or \
                            args.inversions != parser.get_default("inversions") or \
                            args.skip_root

    if args.chords and combination_mode_args:
        parser.error("Argument --chords cannot be used with -r, -t, -i, or --skip-root.")
    if not args.chords and not combination_mode_args:
         # If no chords and no combination args changed from default, run default combination
         logging.info("No specific chords or custom combinations provided. Running default combinations.")
         args.roots = parser.get_default("roots")
         args.types = parser.get_default("types")
         args.inversions = parser.get_default("inversions")


    # --- Determine chords to generate ---
    chords_to_process: List[Tuple[str, str, int]] = []

    if args.chords:
        logging.info(f"Processing specific chords: {', '.join(args.chords)}")
        for chord_str in args.chords:
            parsed = parse_chord_string(chord_str)
            if parsed:
                chords_to_process.append(parsed)
            else:
                logging.warning(f"Skipping unparseable chord: '{chord_str}'")

    else: # Combination mode
        # Filter invalid types/roots specified by user
        requested_roots = [r for r in args.roots if r in VALID_ROOTS]
        invalid_roots = [r for r in args.roots if r not in VALID_ROOTS]
        if invalid_roots:
            logging.warning(f"Ignoring invalid root notes specified: {', '.join(invalid_roots)}")

        requested_types = [t for t in args.types if t in VALID_TYPES] # Assuming internal types are valid
        # We don't validate types here as they map to internal ones

        if not requested_roots or not requested_types:
            logging.error("No valid roots or types available for combination mode. Exiting.")
            return

        logging.info(f"Generating combinations for roots: {', '.join(requested_roots)}")
        logging.info(f"Chord types: {', '.join(requested_types)}")
        logging.info(f"Requested inversions: {', '.join(map(str, sorted(list(set(args.inversions)))))}")

        for root in requested_roots:
            for chord_type in requested_types:
                num_notes = len(INTERVALS[chord_type])
                valid_requested_inversions = [inv for inv in args.inversions if 0 <= inv < num_notes]

                if args.skip_root and 0 in valid_requested_inversions:
                     valid_requested_inversions.remove(0)

                active_inversions = sorted(list(set(valid_requested_inversions)))

                for inversion in active_inversions:
                    chords_to_process.append((root, chord_type, inversion))

    if not chords_to_process:
        logging.error("No valid chords to generate. Exiting.")
        return

    # --- Filename Generation ---
    if args.output is None:
        output_filename = generate_filename(args) # Pass args to let it decide naming based on mode
    else:
        output_filename = args.output
        if not output_filename.lower().endswith(".pdf"):
            output_filename += ".pdf"
    logging.info(f"Output file: {output_filename}")

    # --- PDF Generation ---
    count = 0
    with PdfPages(output_filename) as pdf:
        for root, chord_type, inversion in chords_to_process:
            try:
                notes, keys, title = generate_chord_structure(root, chord_type, inversion)
                plot_chord_diagram(notes, keys, title)
                pdf.savefig(bbox_inches="tight")
                plt.close()
                count += 1
                logging.info(f"Generated diagram for: {root} {chord_type} inv{inversion}")
            except ValueError as e:
                logging.error(f"Skipping: {e}") # Error generating structure (e.g., invalid inversion)
            except Exception as e:
                logging.error(f"Unexpected error generating diagram for {root} {chord_type} inv{inversion}: {e}", exc_info=True)

    logging.info(f"Finished! Created {output_filename} containing {count} chord diagrams.")


if __name__ == "__main__":
    main()