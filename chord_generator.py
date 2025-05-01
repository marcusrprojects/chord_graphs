# chord_generator.py

import itertools
import argparse
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.backends.backend_pdf import PdfPages
import logging
import re
import os  # Import os module
from typing import List, Tuple, Optional, Dict

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
CHORD_TYPE_MAP = {
    "maj": "major", "major": "major", "": "major", "M": "major",
    "min": "minor", "minor": "minor", "m": "minor", "-": "minor",
    "7": "7", "dom7": "7",
    "m7": "minor7", "min7": "minor7", "-7": "minor7",
    "maj7": "maj7", "M7": "maj7",
}
VALID_TYPES = set(INTERVALS.keys())
VALID_ROOTS = set(CHROMATIC_SCALE)

# --- Helper Functions ---

def sanitize_filename(text: str) -> str:
    """Removes or replaces characters invalid for filenames."""
    # Replace # with s (for sharp)
    text = text.replace("#", "s")
    # Replace spaces and parentheses with underscores
    text = re.sub(r"[ \(\)]+", "_", text)
    # Remove any remaining characters that are not alphanumeric, underscore, or hyphen
    text = re.sub(r"[^a-zA-Z0-9_\-]", "", text)
    # Collapse multiple underscores
    text = re.sub(r"_+", "_", text)
    # Remove leading/trailing underscores
    text = text.strip('_')
    return text

def get_chord_notes(root: str, chord_type: str, intervals: List[int]) -> List[str]:
    """Calculates the note names for a chord given intervals."""
    root_index = CHROMATIC_SCALE.index(root)
    chord_notes_indices = [(root_index + interval) % 12 for interval in intervals]
    return [CHROMATIC_SCALE[note_index] for note_index in chord_notes_indices]

# --- Core Chord Logic ---
def generate_chord_structure(root: str, chord_type: str, inversion: int = 0) -> Tuple[List[str], List[str], str]:
    if chord_type not in INTERVALS:
        raise ValueError(f"Unsupported chord type: {chord_type}")
    if root not in VALID_ROOTS:
         raise ValueError(f"Invalid root note: {root}")
    chord_intervals = INTERVALS[chord_type][:]
    num_notes = len(chord_intervals)
    if inversion >= num_notes:
         raise ValueError(f"Inversion {inversion} is invalid for a {num_notes}-note chord ({root} {chord_type})")
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
    title = f"{root} {chord_type} {inversion_str}"
    return chord_note_names, key_colors, title


# --- Chord String Parsing ---
def parse_chord_string(chord_string: str) -> Optional[Tuple[str, str, int]]:
    match = re.match(r"^(?P<root>[A-G]#?)(?P<type>\w*?|)(?:/(?P<bass>[A-G]#?))?$", chord_string.strip())
    if not match:
        logging.warning(f"Could not parse chord string: '{chord_string}'")
        return None
    root = match.group("root")
    type_suffix = match.group("type")
    bass_note = match.group("bass")
    if root not in VALID_ROOTS:
        logging.warning(f"Invalid root note '{root}' in string: '{chord_string}'")
        return None
    chord_type = CHORD_TYPE_MAP.get(type_suffix.lower())
    if chord_type is None:
        logging.warning(f"Unknown chord type suffix '{type_suffix}' in string: '{chord_string}'")
        return None
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
        except Exception as e:
             logging.error(f"Error determining inversion for '{chord_string}': {e}")
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
    # Create a new figure context for each plot
    fig = plt.figure(figsize=(8, 4))
    nx.draw(
        graph,
        pos=positions,
        with_labels=False,
        node_size=2500,
        node_color=node_colors_map,
        edge_color="gray",
        width=1.5,
    )
    for node_id, (x, y) in positions.items():
        node_attr = graph.nodes[node_id]
        plt.text(
            x, y, node_attr['label'],
            fontsize=14, fontweight='bold', ha="center", va="center",
            color=node_attr['text_color']
        )
    plt.title(title, color="gray", fontsize=20, pad=20)
    plt.tight_layout()
    current_ylim = plt.ylim()
    plt.ylim(current_ylim[0] - 0.1, current_ylim[1] + 0.1)
    plt.axis("off")
    # Return the figure object so it can be saved by the caller
    return fig


def generate_pdf_base_name(args):
    """Generates a descriptive base filename for the PDF output."""
    # If specific chords are given, use a simpler naming scheme
    if args.chords:
        prefix = "CustomChords"
        if args.chords:
            safe_chord_names = [sanitize_filename(c) for c in args.chords[:3]]
            prefix = "-".join(safe_chord_names)
            if len(args.chords) > 3:
                prefix += "_etc"
        return prefix

    # --- Combination Mode ---
    default_roots = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    default_types = ["major", "minor", "7", "minor7", "maj7"]
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
    # Sanitize the combined name as well
    return sanitize_filename(base_filename)

# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(
        description="Generate musical chord diagrams. Provide EITHER --chords OR combination flags (-r, -t, -i).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Show defaults in help
    )
    # Input Modes
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("-c", "--chords", nargs='+',
                             help="List of specific chord strings (e.g., 'Cmaj7' 'G7/B' 'Am').")
    # Combination Mode (will be ignored if --chords is used, but defined for defaults)
    parser.add_argument("-r", "--roots", nargs='+', default=CHROMATIC_SCALE, help="List of root notes for combination mode.")
    parser.add_argument("-t", "--types", nargs='+', default=list(INTERVALS.keys()), help="List of chord types for combination mode.")
    parser.add_argument("-i", "--inversions", type=int, nargs='+', default=[0, 1, 2, 3], help="List of inversion numbers for combination mode.")
    parser.add_argument("--skip-root", action='store_true', help="Skip root position in combination mode.")

    # Output Options
    parser.add_argument("--format", choices=['pdf', 'png', 'jpg'], default='pdf',
                        help="Output format.")
    parser.add_argument("--output-dir", default='./chord_graphs',
                        help="Directory to save output file(s).")

    args = parser.parse_args()

    # --- Determine chords to generate ---
    chords_to_process: List[Tuple[str, str, int]] = []
    is_combination_mode = not args.chords

    if args.chords:
        # Specific Chords Mode
        logging.info(f"Processing specific chords: {', '.join(args.chords)}")
        for chord_str in args.chords:
            parsed = parse_chord_string(chord_str)
            if parsed:
                chords_to_process.append(parsed)
            else:
                logging.warning(f"Skipping unparseable chord: '{chord_str}'")
    else:
        # Combination Mode
        # Check if defaults were used (to avoid logging giant lists)
        roots_to_log = args.roots if len(args.roots) < len(CHROMATIC_SCALE) else ['All Defaults']
        types_to_log = args.types if len(args.types) < len(INTERVALS) else ['All Defaults']
        logging.info(f"Generating combinations for roots: {', '.join(roots_to_log)}")
        logging.info(f"Chord types: {', '.join(types_to_log)}")
        logging.info(f"Requested inversions: {', '.join(map(str, sorted(list(set(args.inversions)))))}")

        # Filter invalid types/roots (shouldn't happen with defaults, but good practice)
        requested_roots = [r for r in args.roots if r in VALID_ROOTS]
        requested_types = [t for t in args.types if t in VALID_TYPES]

        if not requested_roots or not requested_types:
            logging.error("No valid roots or types available for combination mode. Exiting.")
            return

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

    # --- Prepare Output Directory ---
    try:
        os.makedirs(args.output_dir, exist_ok=True)
        logging.info(f"Ensured output directory exists: {args.output_dir}")
    except OSError as e:
        logging.error(f"Could not create output directory '{args.output_dir}': {e}")
        return

    # --- Generate and Save Output ---
    count = 0
    if args.format == 'pdf':
        # PDF Mode: Generate base name and save all to one file
        pdf_base_name = generate_pdf_base_name(args)
        pdf_filepath = os.path.join(args.output_dir, f"{pdf_base_name}.pdf")
        logging.info(f"Generating PDF: {pdf_filepath}")
        try:
            with PdfPages(pdf_filepath) as pdf:
                for root, chord_type, inversion in chords_to_process:
                    try:
                        notes, keys, title = generate_chord_structure(root, chord_type, inversion)
                        fig = plot_chord_diagram(notes, keys, title) # Get the figure object
                        pdf.savefig(fig, bbox_inches="tight") # Save the figure to PDF
                        plt.close(fig) # Close the specific figure
                        count += 1
                        logging.info(f"Added diagram to PDF: {title}")
                    except ValueError as e:
                        logging.error(f"Skipping chord {root} {chord_type} inv{inversion} for PDF: {e}")
                    except Exception as e:
                        logging.error(f"Unexpected PDF generation error for {root} {chord_type} inv{inversion}: {e}", exc_info=True)
        except Exception as e:
             logging.error(f"Failed to open or write PDF file '{pdf_filepath}': {e}")
             return

    else:
        # Image Mode (PNG/JPG): Save each plot individually
        logging.info(f"Generating individual {args.format.upper()} files in: {args.output_dir}")
        for root, chord_type, inversion in chords_to_process:
             try:
                notes, keys, title = generate_chord_structure(root, chord_type, inversion)
                fig = plot_chord_diagram(notes, keys, title) # Get the figure object

                # Create individual filename
                img_filename = sanitize_filename(title) + f".{args.format}"
                img_filepath = os.path.join(args.output_dir, img_filename)

                # Save the individual figure
                fig.savefig(img_filepath, format=args.format, bbox_inches="tight")
                plt.close(fig) # Close the specific figure
                count += 1
                logging.info(f"Saved image: {img_filepath}")
             except ValueError as e:
                 logging.error(f"Skipping image for chord {root} {chord_type} inv{inversion}: {e}")
             except Exception as e:
                 logging.error(f"Unexpected image generation error for {root} {chord_type} inv{inversion}: {e}", exc_info=True)

    logging.info(f"Finished! Generated {count} diagram(s) in '{args.output_dir}' as {args.format.upper()}.")


if __name__ == "__main__":
    main()