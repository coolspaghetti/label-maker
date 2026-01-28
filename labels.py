import pandas as pd # used to handle CSV files
import hashlib # used to create hashes
import os # used to handle file paths
# reportlab is used to handle PDF generation
from reportlab.lib.pagesizes import A4 
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import mm

# =========================
# NORMALIZATION & HASHING
# =========================
def norm(s):
    if pd.isna(s): # isna() handles missing values in cells
        return ""
    return str(s).lower().strip() 
# don't forget to cast as string because there's a number column which doesn't have a .lower()

def row_to_string(row):
    return "|".join([
        norm(row["Magazine"]),
        norm(row["Edition"]),
        norm(row["Year"])
    ])

def hash_row(row):
    s = row_to_string(row)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# hash filename for mode
def hash_file_for_mode(mode):
    return f"printed_{mode}.hashes"

# load previously printed hashes
def load_hashes(mode):
    path = hash_file_for_mode(mode)
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return set(line.strip() for line in f)

# save printed hashes
def save_hashes(hashes, mode):
    path = hash_file_for_mode(mode)
    with open(path, "w") as f:
        for h in sorted(hashes):
            f.write(h + "\n")

# filter new labels
def filter_new(df, mode):
    known = load_hashes(mode)
    new_rows = []
    new_hashes = set(known)

    for _, row in df.iterrows():
        h = hash_row(row)
        if h not in known:
            new_rows.append(row)
            new_hashes.add(h)
    
    return new_rows, new_hashes

# =========================
# LABEL GENERATION
# =========================
def generate_labels(rows, mode="clippings"):
    c = canvas.Canvas(f"labels_{mode}.pdf", pagesize=A4)
    width, height = A4

    # =========================
    # LABEL CONFIG BY MODE
    # =========================
    if mode == "clippings":
        label_w = 50 * 2.83 # 1 mm = 2.83 points
        label_h = 13 * 2.83

        mag_style_name = "mag"
        edition_style_name = "edition"

        left_margin = 6
        right_margin = 6
        top_margin = 4
        bottom_margin = 6
        line_gap = 2

    else: # magazines
        label_w = 30 * 2.83
        label_h = 15 * 2.83

        mag_style_name = "mini_mag"
        edition_style_name = "mini_edition"

        left_margin = 4
        right_margin = 4
        top_margin = 3
        bottom_margin = 4
        line_gap = 1

    # =========================
    # PAGE & GRID CALCULATION
    # =========================
    page_margin_left = 20
    page_margin_right = 20
    page_margin_top = 20
    page_margin_bottom = 20

    usable_width = width - page_margin_left - page_margin_right
    usable_height = height - page_margin_top - page_margin_bottom

    cols = int(usable_width // label_w)
    rows_per_page = int(usable_height // label_h)


    # =========================
    # TEXT STYLES
    # =========================
    styles = getSampleStyleSheet()

    mag_style = ParagraphStyle(
        "Magazine", 
        parent=styles["Normal"], 
        fontName="Helvetica-Bold", 
        fontSize=10,
        alignment=TA_LEFT
    )
    edition_style = ParagraphStyle(
        "Edition", 
        parent=styles["Normal"], 
        fontName="Helvetica", 
        fontSize=9, 
        alignment=TA_LEFT
    )
    mini_mag_style = ParagraphStyle(
        "MiniMagazine",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=9,
        spaceAfter=0,
        spaceBefore=0,
        alignment=TA_LEFT
    )
    mini_edition_style = ParagraphStyle(
        "MiniEdition",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=8,
        spaceAfter=0,
        spaceBefore=0,
        alignment=TA_LEFT
    )

    style_map = {
        "mag": mag_style,
        "edition": edition_style,
        "mini_mag": mini_mag_style,
        "mini_edition": mini_edition_style
    }

    # =========================
    # STARTING POSITIONS
    # =========================
    grid_width = cols * label_w
    grid_height = rows_per_page * label_h

    x0 = page_margin_left + (usable_width - grid_width) / 2
    y0 = height - page_margin_top


    # =========================
    # DRAW LABELS
    # =========================
    i = 0
    for row in rows:
        col = i % cols
        row_i = (i // cols) % rows_per_page

        x = x0 + col * label_w
        y = y0 - row_i * label_h

        # draw dashed border
        c.setDash(3, 3)
        c.rect(x, y - label_h, label_w, label_h)
        c.setDash()

        # usable text area
        w = label_w - left_margin - right_margin
        h = label_h - top_margin - bottom_margin

        cursor = y - top_margin
        if mode == "magazines":
            cursor -= 1

        # magazine name
        p1 = Paragraph(row["Magazine"], style_map[mag_style_name])
        w1, h1 = p1.wrap(w, h)
        p1.drawOn(c, x + left_margin, cursor - h1)
        cursor -= h1 + line_gap

        # edition / year
        p2 = Paragraph(f"{row['Edition']}/{row['Year']}", style_map[edition_style_name])
        w2, h2 = p2.wrap(w, h)
        p2.drawOn(c, x + left_margin, cursor - h2)

        # next label
        i += 1
        if i % (cols * rows_per_page) == 0:
            c.showPage()

    c.save()

# =========================
# USER INPUT
# =========================
mode = input("Process clippings or magazines? [c/m]: ").strip().lower()
if mode not in ("c", "m"):
    raise ValueError("Please enter 'c' for clippings or 'm' for magazines!")

mode = "clippings" if mode == "c" else "magazines"

csv_name = input("Enter CSV filename (must be in this folder): ").strip()
if not csv_name.endswith(".csv"):
    csv_name += ".csv"

if not os.path.exists(csv_name):
    raise FileNotFoundError(f"File '{csv_name}' not found!")

# =========================
# LOAD & PROCESS DATA
# =========================
df = pd.read_csv(csv_name, sep=";") # separator is ; because Europe (comma is used as decimal point here)

# filter new rows
new_rows, new_hashes = filter_new(df, mode)

if len(new_rows) == 0:
    print("No new labels.")
else:
    generate_labels(new_rows, mode=mode)
    save_hashes(new_hashes, mode)
    print(f"Generated {len(new_rows)} {mode} labels.")
