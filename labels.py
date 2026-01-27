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




# normalize string for hashing
def norm(s):
    if pd.isna(s): # isna() handles missing values in cells
        return ""
    return str(s).lower().strip() 
# don't forget to cast as string because there's a number column which doesn't have a .lower()

# convert a row to a string
def row_to_string(row):
    return "|".join([
        norm(row["Magazine"]),
        norm(row["Edition"]),
        norm(row["Year"])
    ])

# add hashing
def hash_row(row):
    s = row_to_string(row)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# create memory file
# load previously printed hashes
def load_hashes():
    if not os.path.exists("printed.hashes"):
        return set()
    with open("printed.hashes") as f:
        return set(line.strip() for line in f)

# save printed hashes
def save_hashes(hashes):
    with open("printed.hashes", "w") as f:
        for h in sorted(hashes):
            f.write(h + "\n")

# filter new labels
def filter_new(df):
    known = load_hashes()
    new_rows = []
    new_hashes = set(known)

    for _, row in df.iterrows():
        h = hash_row(row)
        if h not in known:
            new_rows.append(row)
            new_hashes.add(h)
    
    return new_rows, new_hashes

# generate labels PDF
def generate_labels(rows):
    c = canvas.Canvas("labels.pdf", pagesize=A4)
    width, height = A4

    # label size in points (1 mm = 2.83 points)
    label_w = 70 * 2.83
    label_h = 17 * 2.83
    cols = 3
    rows_per_page = 8

    # margins inside label
    left_margin = 10
    right_margin = 10
    top_margin = 10
    bottom_margin = 10

    # text styles
    styles = getSampleStyleSheet()
    mag_style = ParagraphStyle(
        "Magazine", 
        parent=styles["Normal"], 
        fontName="Helvetica-Bold", 
        fontSize=12, 
        alignment=TA_LEFT
    )
    edition_style = ParagraphStyle(
        "Edition", 
        parent=styles["Normal"], 
        fontName="Helvetica", 
        fontSize=12, 
        alignment=TA_LEFT
    )

    # starting positions
    x0 = 20
    y0 = height - 40

    # draw labels
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

        y_text = y - top_margin

        # draw text
        cursor = y_text

        # magazine name
        p1 = Paragraph(row["Magazine"], mag_style)
        w1, h1 = p1.wrap(w, h)
        p1.drawOn(c, x + left_margin, cursor - h1)
        cursor -= h1 + 2

        # edition/year
        p2 = Paragraph(f"{row['Edition']}/{row['Year']}", edition_style)
        w2, h2 = p2.wrap(w, h)
        p2.drawOn(c, x + left_margin, cursor - h2)

        # next label
        i += 1
        if i % (cols * rows_per_page) == 0:
            c.showPage()

    c.save()

# load data
df = pd.read_csv("test.csv", sep=";") # separator is ; because it's from a European source (comma is used as decimal point here)

# filter new rows
new_rows, new_hashes = filter_new(df)

if len(new_rows) == 0:
    print("No new labels.")
else:
    generate_labels(new_rows)
    save_hashes(new_hashes)
    print("Generated", len(new_rows), "labels.")
