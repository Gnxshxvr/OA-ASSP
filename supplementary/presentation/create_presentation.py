"""Refined generator script for OA-ASSP DAA DA1 Survey Presentation.
Creates exactly 17 main content slides in widescreen 16:9 format using python-pptx,
with strict left-alignment, top vertical anchoring, clean vector diagrams, and zero overlap.
"""

import os
import sys
from pathlib import Path
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

# -------------------------------------------------------------------------
# COLOR PALETTE (Professional Academic Engineering Theme)
# -------------------------------------------------------------------------
COLOR_PRIMARY_NAVY = RGBColor(26, 54, 93)       # #1A365D - Deep Academic Navy
COLOR_SECONDARY_BLUE = RGBColor(37, 99, 235)    # #2563EB - Royal / Academic Blue
COLOR_DARK_TEXT = RGBColor(15, 23, 42)          # #0F172A - Slate 900 (Headings)
COLOR_BODY_TEXT = RGBColor(51, 65, 85)          # #334155 - Slate 700 (Body)
COLOR_MUTED_TEXT = RGBColor(100, 116, 139)      # #64748B - Slate 500 (Footers/Meta)
COLOR_CARD_BG = RGBColor(248, 250, 252)         # #F8FAFC - Slate 50 (Card fill)
COLOR_CARD_BORDER = RGBColor(226, 232, 240)     # #E2E8F0 - Slate 200 (Dividers/Borders)
COLOR_ACCENT_AMBER = RGBColor(180, 83, 9)       # #B45309 - Refined Amber
COLOR_ACCENT_GREEN = RGBColor(22, 101, 52)      # #166534 - Forest Green (Affordable/VBS)
COLOR_RELEVANCE_BG = RGBColor(238, 242, 255)    # #EEF2FF - Soft Indigo Tint for Relevance
COLOR_RELEVANCE_BORDER = RGBColor(99, 102, 241) # #6366F1 - Indigo Border
COLOR_WHITE = RGBColor(255, 255, 255)

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"

def set_shape_flat(shape, fill_color, border_color=None, border_width=1):
    """Sets flat solid fill and clean border on a shape."""
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(border_width)
    else:
        shape.line.fill.background()

def add_header(slide, title_text, category_text):
    """Creates a consistent, elegant slide header."""
    # Category / Tracker tag
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.38), Inches(11.733), Inches(0.28))
    tf_cat = cat_box.text_frame
    tf_cat.word_wrap = True
    tf_cat.margin_left = tf_cat.margin_top = tf_cat.margin_right = tf_cat.margin_bottom = 0
    p_cat = tf_cat.paragraphs[0]
    p_cat.text = category_text.upper()
    p_cat.font.name = FONT_HEADING
    p_cat.font.size = Pt(10)
    p_cat.font.bold = True
    p_cat.font.color.rgb = COLOR_SECONDARY_BLUE
    p_cat.alignment = PP_ALIGN.LEFT

    # Slide Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.66), Inches(11.733), Inches(0.55))
    tf_title = title_box.text_frame
    tf_title.word_wrap = True
    tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
    p_title = tf_title.paragraphs[0]
    p_title.text = title_text
    p_title.font.name = FONT_HEADING
    p_title.font.size = Pt(21)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_PRIMARY_NAVY
    p_title.alignment = PP_ALIGN.LEFT

    # Subtle divider rule
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.22), Inches(11.733), Inches(0.015))
    set_shape_flat(line, COLOR_CARD_BORDER)

def add_footer(slide, current_slide, total_slides=17):
    """Adds a clean academic footer with divider and slide number."""
    # Divider line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.92), Inches(11.733), Inches(0.015))
    set_shape_flat(line, COLOR_CARD_BORDER)

    # Footer text left
    foot_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.98), Inches(9.0), Inches(0.3))
    tf = foot_box.text_frame
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "DAA DA1 Literature Survey & Research Presentation | OA-ASSP Study | VIT Chennai"
    p.font.name = FONT_BODY
    p.font.size = Pt(9.5)
    p.font.color.rgb = COLOR_MUTED_TEXT
    p.alignment = PP_ALIGN.LEFT

    # Footer text right (slide number)
    num_box = slide.shapes.add_textbox(Inches(10.0), Inches(6.98), Inches(2.533), Inches(0.3))
    tf_num = num_box.text_frame
    tf_num.margin_left = tf_num.margin_top = tf_num.margin_right = tf_num.margin_bottom = 0
    p_num = tf_num.paragraphs[0]
    p_num.text = f"Slide {current_slide} of {total_slides}"
    p_num.alignment = PP_ALIGN.RIGHT
    p_num.font.name = FONT_HEADING
    p_num.font.size = Pt(10)
    p_num.font.bold = True
    p_num.font.color.rgb = COLOR_PRIMARY_NAVY

# -------------------------------------------------------------------------
# BUILD PRESENTATION
# -------------------------------------------------------------------------
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

# =========================================================================
# SLIDE 1: TITLE SLIDE
# =========================================================================
slide1 = prs.slides.add_slide(blank_layout)

# Decorative subtle accent bar on left
accent_bar = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.3), Inches(0.12), Inches(5.3))
set_shape_flat(accent_bar, COLOR_SECONDARY_BLUE)

# Title & Subtitle in primary text box
title_box = slide1.shapes.add_textbox(Inches(1.2), Inches(1.2), Inches(11.3), Inches(2.3))
tf = title_box.text_frame
tf.word_wrap = True
tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

p_course = tf.paragraphs[0]
p_course.text = "DESIGN AND ANALYSIS OF ALGORITHMS (DAA) — DA1 LITERATURE SURVEY & RESEARCH"
p_course.font.name = FONT_HEADING
p_course.font.size = Pt(11)
p_course.font.bold = True
p_course.font.color.rgb = COLOR_SECONDARY_BLUE
p_course.space_after = Pt(10)
p_course.alignment = PP_ALIGN.LEFT

p_main = tf.add_paragraph()
p_main.text = "When Is Algorithm Selection Worth the Cost?"
p_main.font.name = FONT_HEADING
p_main.font.size = Pt(32)
p_main.font.bold = True
p_main.font.color.rgb = COLOR_PRIMARY_NAVY
p_main.space_after = Pt(8)
p_main.alignment = PP_ALIGN.LEFT

p_sub = tf.add_paragraph()
p_sub.text = "An Overhead-Aware Study of Exact Shortest-Path Computation"
p_sub.font.name = FONT_BODY
p_sub.font.size = Pt(18)
p_sub.font.color.rgb = COLOR_BODY_TEXT
p_sub.alignment = PP_ALIGN.LEFT

# Research Question Card
ctx_card = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(3.7), Inches(11.3), Inches(0.85))
set_shape_flat(ctx_card, COLOR_CARD_BG, COLOR_CARD_BORDER)
tf_ctx = ctx_card.text_frame
tf_ctx.vertical_anchor = MSO_ANCHOR.TOP
tf_ctx.word_wrap = True
tf_ctx.margin_left = Inches(0.25)
tf_ctx.margin_top = Inches(0.15)
tf_ctx.margin_right = Inches(0.25)

p_ctx = tf_ctx.paragraphs[0]
p_ctx.text = "Central Research Question: "
p_ctx.font.name = FONT_HEADING
p_ctx.font.size = Pt(11)
p_ctx.font.bold = True
p_ctx.font.color.rgb = COLOR_PRIMARY_NAVY
p_ctx.alignment = PP_ALIGN.LEFT

run_ctx = p_ctx.add_run()
run_ctx.text = '"Within what graph and query-workload conditions can adaptive exact shortest-path algorithm selection capture enough SBS–VBS performance headroom to justify its own selection overhead?"'
run_ctx.font.name = FONT_BODY
run_ctx.font.size = Pt(11)
run_ctx.font.italic = True
run_ctx.font.color.rgb = COLOR_BODY_TEXT

# Team Details Card
team_card = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(4.75), Inches(11.3), Inches(1.85))
set_shape_flat(team_card, COLOR_WHITE, COLOR_CARD_BORDER)
tf_team = team_card.text_frame
tf_team.vertical_anchor = MSO_ANCHOR.TOP
tf_team.word_wrap = True
tf_team.margin_left = Inches(0.3)
tf_team.margin_top = Inches(0.18)
tf_team.margin_right = Inches(0.3)

p_tlabel = tf_team.paragraphs[0]
p_tlabel.text = "RESEARCH TEAM & AFFILIATION:"
p_tlabel.font.name = FONT_HEADING
p_tlabel.font.size = Pt(10)
p_tlabel.font.bold = True
p_tlabel.font.color.rgb = COLOR_MUTED_TEXT
p_tlabel.space_after = Pt(6)
p_tlabel.alignment = PP_ALIGN.LEFT

p_names = tf_team.add_paragraph()
p_names.text = "1. Ganeshvar K S          2. Sai Siddaarth          3. Uma Maheshwari"
p_names.font.name = FONT_HEADING
p_names.font.size = Pt(14)
p_names.font.bold = True
p_names.font.color.rgb = COLOR_PRIMARY_NAVY
p_names.space_after = Pt(6)
p_names.alignment = PP_ALIGN.LEFT

p_affil = tf_team.add_paragraph()
p_affil.text = "School of Computer Science\nVellore Institute of Technology, Chennai, India"
p_affil.font.name = FONT_BODY
p_affil.font.size = Pt(11.5)
p_affil.font.color.rgb = COLOR_BODY_TEXT
p_affil.alignment = PP_ALIGN.LEFT

add_footer(slide1, 1)

# =========================================================================
# SLIDE 2: INTRODUCTION & PROBLEM CONTEXT
# =========================================================================
slide2 = prs.slides.add_slide(blank_layout)
add_header(slide2, "The Overhead Dilemma in Shortest-Path Selection", "Background & Motivation")

# Left Column: Concepts (Width: 5.9")
left_card = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.35), Inches(5.8), Inches(5.4))
set_shape_flat(left_card, COLOR_WHITE, COLOR_CARD_BORDER)
tf_l = left_card.text_frame
tf_l.vertical_anchor = MSO_ANCHOR.TOP
tf_l.word_wrap = True
tf_l.margin_left = Inches(0.25)
tf_l.margin_top = Inches(0.2)
tf_l.margin_right = Inches(0.25)

p = tf_l.paragraphs[0]
p.text = "Algorithmic Dilemma: Headroom vs. Overhead"
p.font.name = FONT_HEADING
p.font.size = Pt(13.5)
p.font.bold = True
p.font.color.rgb = COLOR_PRIMARY_NAVY
p.space_after = Pt(12)
p.alignment = PP_ALIGN.LEFT

bullets_s2 = [
    ("Algorithmic Diversity:", " Canonical exact solvers (Dijkstra, Bidirectional Dijkstra, A*) have fundamentally different strengths. No single solver dominates across all topological configurations and query endpoints."),
    ("Instance Complementarity:", " Graph density, diameter, and coordinate embeddings favor different algorithms per instance (e.g., A* excels on metric embeddings, Bidirectional Dijkstra on dense random graphs)."),
    ("The Selection Promise:", " Per-instance algorithm selection seeks to map instance features to the fastest solver dynamically, aiming to outperform any static solver policy."),
    ("The Microsecond Reality:", " Exact shortest-path queries on sub-thousand-vertex graphs execute in hundreds of microseconds. Standard ML inference and feature extraction can easily exceed solver execution time!"),
    ("The Core Question:", " Does adaptive algorithm selection capture enough solver-side performance gain to pay for the computational cost of extracting features and running the model?")
]

for title_b, text_b in bullets_s2:
    p_b = tf_l.add_paragraph()
    p_b.text = "• "
    p_b.font.name = FONT_BODY
    p_b.font.size = Pt(11)
    p_b.font.color.rgb = COLOR_SECONDARY_BLUE
    p_b.space_after = Pt(8)
    p_b.alignment = PP_ALIGN.LEFT
    
    r1 = p_b.add_run()
    r1.text = title_b
    r1.font.bold = True
    r1.font.color.rgb = COLOR_DARK_TEXT
    
    r2 = p_b.add_run()
    r2.text = text_b
    r2.font.bold = False
    r2.font.color.rgb = COLOR_BODY_TEXT

# Right Column: Visual Pipeline & Cost Formula (Width: 5.7")
right_card = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.35), Inches(5.733), Inches(5.4))
set_shape_flat(right_card, COLOR_CARD_BG, COLOR_CARD_BORDER)
tf_r = right_card.text_frame
tf_r.vertical_anchor = MSO_ANCHOR.TOP
tf_r.word_wrap = True
tf_r.margin_left = Inches(0.25)
tf_r.margin_top = Inches(0.2)
tf_r.margin_right = Inches(0.25)

p_rt = tf_r.paragraphs[0]
p_rt.text = "End-to-End Decision & Execution Pipeline"
p_rt.font.name = FONT_HEADING
p_rt.font.size = Pt(13.5)
p_rt.font.bold = True
p_rt.font.color.rgb = COLOR_PRIMARY_NAVY
p_rt.space_after = Pt(10)
p_rt.alignment = PP_ALIGN.LEFT

# Flow steps in right card
steps = [
    ("1. Resident Graph G", "One-time graph features computed once, amortized over workload Q"),
    ("2. Incoming Query (s, t)", "Per-query features extracted (endpoints, degrees, heuristic distance)"),
    ("3. Algorithm Selector", "Decision tree evaluates features (Library vs. Compiled branch inference)"),
    ("4. Solver Execution", "Selected solver executes: Dijkstra, Bidirectional Dijkstra, or A*"),
    ("5. Path & Distance", "Optimal path returned. Total time = Selection Cost + Solver Cost")
]

for s_title, s_desc in steps:
    p_s = tf_r.add_paragraph()
    p_s.text = f"▶ {s_title}"
    p_s.font.name = FONT_HEADING
    p_s.font.size = Pt(11)
    p_s.font.bold = True
    p_s.font.color.rgb = COLOR_SECONDARY_BLUE
    p_s.alignment = PP_ALIGN.LEFT
    
    p_sd = tf_r.add_paragraph()
    p_sd.text = f"    {s_desc}"
    p_sd.font.name = FONT_BODY
    p_sd.font.size = Pt(10)
    p_sd.font.color.rgb = COLOR_BODY_TEXT
    p_sd.space_after = Pt(5)
    p_sd.alignment = PP_ALIGN.LEFT

# Formula Callout at bottom of right card
f_box = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.0), Inches(5.45), Inches(5.333), Inches(1.15))
set_shape_flat(f_box, COLOR_WHITE, COLOR_SECONDARY_BLUE, border_width=1.5)
tf_f = f_box.text_frame
tf_f.vertical_anchor = MSO_ANCHOR.TOP
tf_f.word_wrap = True
tf_f.margin_left = Inches(0.18)
tf_f.margin_top = Inches(0.1)

p_fe = tf_f.paragraphs[0]
p_fe.text = "TOTAL ADAPTIVE COST FORMULATION:"
p_fe.font.name = FONT_HEADING
p_fe.font.size = Pt(9.5)
p_fe.font.bold = True
p_fe.font.color.rgb = COLOR_SECONDARY_BLUE
p_fe.space_after = Pt(3)
p_fe.alignment = PP_ALIGN.LEFT

p_eq = tf_f.add_paragraph()
p_eq.text = "C_adaptive(Q) = C_graph_feat + ∑ (C_query_feat + C_sel + C_solver)"
p_eq.font.name = "Consolas"
p_eq.font.size = Pt(10)
p_eq.font.bold = True
p_eq.font.color.rgb = COLOR_DARK_TEXT
p_eq.space_after = Pt(2)
p_eq.alignment = PP_ALIGN.LEFT

p_bal = tf_f.add_paragraph()
p_bal.text = "Break-Even Condition: Solver Savings > Total Selection Overhead"
p_bal.font.name = FONT_HEADING
p_bal.font.size = Pt(9.5)
p_bal.font.bold = True
p_bal.font.color.rgb = COLOR_ACCENT_AMBER
p_bal.alignment = PP_ALIGN.LEFT

add_footer(slide2, 2)

# =========================================================================
# SLIDE 3: OBJECTIVES OF THE SURVEY
# =========================================================================
slide3 = prs.slides.add_slide(blank_layout)
add_header(slide3, "Survey Objectives: Scope & Methodological Goals", "Academic Survey Objectives")

obj_data = [
    ("Objective 1: Exact Shortest-Path Algorithm Foundations",
     "Analyze the mechanics, expansion geometries, and performance trade-offs of canonical point-to-point solvers (Dijkstra, Bidirectional Dijkstra, and A* search) across varied network topologies."),
    ("Objective 2: Principles of Per-Instance Algorithm Selection",
     "Examine the theoretical underpinnings of algorithm portfolios originating from Rice's framework (1976), tracing its evolution through empirical hardness models, runtime prediction, and automated selection."),
    ("Objective 3: Graph Characteristics as Predictive Features",
     "Investigate the topological and metric features (density, degree statistics, clustering, and embedding ratios) used by machine learning models to characterize instances before solver dispatch."),
    ("Objective 4: Computational Cost of Feature Extraction & Inference",
     "Study the wall-clock overhead incurred during instance characterization, vector assembly, and decision-tree inference, identifying when selection latency rivals execution time."),
    ("Objective 5: Critical Comparison of State-of-the-Art Literature",
     "Synthesize and compare methodologies across combinatorial portfolios (SATzilla, ASlib), algorithm engineering (Bast et al.), and recent landscape benchmarking (Gholami Shiri et al., van der Blom)."),
    ("Objective 6: Establish the OA-ASSP Research Gap",
     "Formulate the formal research gap addressed by OA-ASSP: pricing physical wall-clock selection overhead against the empirical SBS–VBS oracle headroom across repeated query workloads.")
]

y_pos = 1.38
card_h = 0.82
for idx, (head, desc) in enumerate(obj_data):
    box = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(y_pos), Inches(11.733), Inches(card_h))
    set_shape_flat(box, COLOR_CARD_BG, COLOR_CARD_BORDER)
    tf_o = box.text_frame
    tf_o.vertical_anchor = MSO_ANCHOR.TOP
    tf_o.word_wrap = True
    tf_o.margin_left = Inches(0.22)
    tf_o.margin_top = Inches(0.1)
    tf_o.margin_right = Inches(0.22)
    
    p_h = tf_o.paragraphs[0]
    p_h.text = head
    p_h.font.name = FONT_HEADING
    p_h.font.size = Pt(11)
    p_h.font.bold = True
    p_h.font.color.rgb = COLOR_PRIMARY_NAVY
    p_h.space_after = Pt(2)
    p_h.alignment = PP_ALIGN.LEFT
    
    p_d = tf_o.add_paragraph()
    p_d.text = desc
    p_d.font.name = FONT_BODY
    p_d.font.size = Pt(10)
    p_d.font.color.rgb = COLOR_BODY_TEXT
    p_d.alignment = PP_ALIGN.LEFT
    
    y_pos += 0.90

add_footer(slide3, 3)

# =========================================================================
# HELPER FOR SLIDES 4-13: STANDARDIZED PAPER SLIDES (EXACTLY 5 BULLETS)
# =========================================================================
def build_paper_slide(prs, slide_idx, paper_num, short_title, citation_info, bullets_5):
    """Constructs a clean, rigorous academic paper review slide with strict left alignment."""
    slide = prs.slides.add_slide(blank_layout)
    cat_str = f"Literature Survey — Paper {paper_num:02d} of 10"
    add_header(slide, short_title, cat_str)
    
    # Metadata bar
    meta_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.32), Inches(11.733), Inches(0.52))
    set_shape_flat(meta_box, COLOR_CARD_BG, COLOR_CARD_BORDER)
    tf_m = meta_box.text_frame
    tf_m.vertical_anchor = MSO_ANCHOR.TOP
    tf_m.word_wrap = True
    tf_m.margin_left = Inches(0.2)
    tf_m.margin_top = Inches(0.12)
    p_m = tf_m.paragraphs[0]
    p_m.text = f"Bibliographic Reference: {citation_info}"
    p_m.font.name = FONT_BODY
    p_m.font.size = Pt(10)
    p_m.font.bold = True
    p_m.font.color.rgb = COLOR_PRIMARY_NAVY
    p_m.alignment = PP_ALIGN.LEFT
    
    # Four standard bullets container (Problem, Approach, Evaluation, Finding)
    std_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.95), Inches(11.733), Inches(3.45))
    set_shape_flat(std_box, COLOR_WHITE, COLOR_CARD_BORDER)
    tf_s = std_box.text_frame
    tf_s.vertical_anchor = MSO_ANCHOR.TOP
    tf_s.word_wrap = True
    tf_s.margin_left = Inches(0.25)
    tf_s.margin_top = Inches(0.18)
    tf_s.margin_right = Inches(0.25)
    
    labels_4 = [
        ("Problem Addressed:", bullets_5[0]),
        ("Main Approach:", bullets_5[1]),
        ("Evaluation & Setting:", bullets_5[2]),
        ("Main Finding:", bullets_5[3])
    ]
    
    for i, (lbl, text_val) in enumerate(labels_4):
        p_row = tf_s.paragraphs[0] if i == 0 else tf_s.add_paragraph()
        p_row.text = "• "
        p_row.font.name = FONT_BODY
        p_row.font.size = Pt(10.5)
        p_row.font.color.rgb = COLOR_SECONDARY_BLUE
        p_row.space_after = Pt(7)
        p_row.alignment = PP_ALIGN.LEFT
        
        r_lbl = p_row.add_run()
        r_lbl.text = f"{lbl} "
        r_lbl.font.bold = True
        r_lbl.font.color.rgb = COLOR_DARK_TEXT
        
        r_txt = p_row.add_run()
        r_txt.text = text_val
        r_txt.font.bold = False
        r_txt.font.color.rgb = COLOR_BODY_TEXT
        
    # Fifth Bullet: Relevance to OA-ASSP Callout Card
    rel_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.5), Inches(11.733), Inches(1.28))
    set_shape_flat(rel_box, COLOR_RELEVANCE_BG, COLOR_RELEVANCE_BORDER, border_width=1.5)
    tf_r = rel_box.text_frame
    tf_r.vertical_anchor = MSO_ANCHOR.TOP
    tf_r.word_wrap = True
    tf_r.margin_left = Inches(0.25)
    tf_r.margin_top = Inches(0.12)
    tf_r.margin_right = Inches(0.25)
    
    p_rh = tf_r.paragraphs[0]
    p_rh.text = "RELEVANCE TO OA-ASSP RESEARCH:"
    p_rh.font.name = FONT_HEADING
    p_rh.font.size = Pt(9.5)
    p_rh.font.bold = True
    p_rh.font.color.rgb = COLOR_RELEVANCE_BORDER
    p_rh.space_after = Pt(2)
    p_rh.alignment = PP_ALIGN.LEFT
    
    p_rb = tf_r.add_paragraph()
    p_rb.text = f"• {bullets_5[4]}"
    p_rb.font.name = FONT_BODY
    p_rb.font.size = Pt(10.5)
    p_rb.font.color.rgb = COLOR_DARK_TEXT
    p_rb.alignment = PP_ALIGN.LEFT
    
    add_footer(slide, slide_idx)

# =========================================================================
# PAPERS 1 TO 10 DATA
# =========================================================================

# Paper 1: Rice (1976)
build_paper_slide(
    prs, slide_idx=4, paper_num=1,
    short_title="Rice (1976) — Foundational Algorithm Selection Model",
    citation_info="John R. Rice, 'The Algorithm Selection Problem', Advances in Computers, Vol. 15, Academic Press, pp. 65–118, 1976.",
    bullets_5=[
        "Formalizing how to systematically choose the most computationally effective algorithm for a given problem instance when algorithm performance varies significantly across instances.",
        "Formulated the foundational four-space conceptual architecture mapping Problem Space (P) via Feature Extraction f(x) into Feature Space (F), which a Selection Mapping S(f) routes to Algorithm Space (A), evaluated in Performance Space (Y).",
        "Theoretical formulation and mathematical analysis illustrated across computational mathematics, numerical quadrature, and differential equation approximation.",
        "Proved that per-instance selection can achieve performance strictly superior to any single static algorithm whenever measurable instance features correlate with performance divergence.",
        "Provides the foundational theoretical framework adopted by OA-ASSP, while highlighting its historical blindspot: Rice's model implicitly assumes feature extraction and selection costs are negligible relative to solver execution time."
    ]
)

# Paper 2: Xu et al. (2008) - SATzilla
build_paper_slide(
    prs, slide_idx=5, paper_num=2,
    short_title="Xu et al. (2008) — SATzilla: Portfolio-Based Selection for SAT",
    citation_info="Lin Xu, Frank Hutter, Holger H. Hoos, Kevin Leyton-Brown, 'SATzilla: Portfolio-based Algorithm Selection for SAT', Journal of Artificial Intelligence Research (JAIR), Vol. 32, pp. 565–606, 2008.",
    bullets_5=[
        "Solving hard propositional satisfiability (SAT) instances where solver performance exhibits extreme variance across industrial, random, and crafted formula distributions.",
        "Constructed empirical hardness models using cost-sensitive ridge regression to predict individual solver runtimes from cheap syntactic features, incorporating automated pre-solving routines and fallback policies.",
        "Comprehensive empirical evaluation across thousands of benchmarks from international SAT Competitions against individual state-of-the-art SAT solvers.",
        "Automated portfolio-based algorithm selection achieved massive, order-of-magnitude speedups over every standalone solver, establishing algorithm selection as a dominant paradigm in SAT.",
        "Demonstrates the immense power of algorithm selection in compute-heavy domains (seconds to hours), contrasting sharply with OA-ASSP's microsecond shortest-path domain where solver runtimes cannot easily absorb feature-extraction delays."
    ]
)

# Paper 3: Hutter et al. (2014) - Runtime Prediction
build_paper_slide(
    prs, slide_idx=6, paper_num=3,
    short_title="Hutter et al. (2014) — Algorithm Runtime Prediction",
    citation_info="Frank Hutter, Lin Xu, Holger H. Hoos, Kevin Leyton-Brown, 'Algorithm Runtime Prediction: Methods & Evaluation', Artificial Intelligence (AIJ), Vol. 206, pp. 79–111, 2014.",
    bullets_5=[
        "Accurately predicting the empirical wall-clock execution runtimes of algorithms on unseen problem instances based on measurable instance characteristics.",
        "Evaluated and compared multiple machine learning regression architectures (ridge regression, neural networks, Gaussian processes, and random forests) to model log-transformed execution times, accounting for timeout censoring.",
        "Extensive cross-domain evaluation spanning propositional satisfiability (SAT), mixed integer programming (MIP), and the traveling salesperson problem (TSP).",
        "Random forests delivered the highest predictive accuracy across heterogeneous benchmarks by effectively capturing complex non-linear feature interactions without catastrophic prediction errors on heavy-tailed runtimes.",
        "Directly motivates OA-ASSP's diagnosis that unweighted 0/1 classification loss fails because it treats small and large timing differences identically, pointing to runtime-loss and regret-aware objectives as crucial future directions."
    ]
)

# Paper 4: Kotthoff (2014) - LLAMA
build_paper_slide(
    prs, slide_idx=7, paper_num=4,
    short_title="Kotthoff (2014) — LLAMA: Modular Algorithm Selection Toolkit",
    citation_info="Lars Kotthoff, 'LLAMA: Leveraging Learning to Automatically Manage Algorithms', AI Communications, Vol. 27, No. 2, pp. 175–182, 2014.",
    bullets_5=[
        "The lack of an open, flexible, and standardized modular toolkit for implementing, comparing, and evaluating diverse algorithm selection models.",
        "Developed an R-based framework providing modular abstractions that decouple feature preprocessing, machine learning models (regression, classification, clustering, pairwise ranking), and evaluation baselines.",
        "Validated across canonical algorithm selection datasets in constraint satisfaction, boolean satisfiability, and combinatorial optimization.",
        "Demonstrated that selection performance is heavily influenced by modeling choices and that pairwise difference ranking frequently outperforms multi-class classification on portfolio tasks.",
        "Informs OA-ASSP's architectural separation of feature tiers, selection policies, and evaluation baselines, while reinforcing the need for selection toolkits to explicitly account for sub-millisecond execution and inference latency."
    ]
)

# Paper 5: Lindauer et al. (2015) - AutoFolio
build_paper_slide(
    prs, slide_idx=8, paper_num=5,
    short_title="Lindauer et al. (2015) — AutoFolio: Configured Algorithm Selection",
    citation_info="Marius Lindauer, Holger H. Hoos, Frank Hutter, Torsten Schaub, 'AutoFolio: An Automatically Configured Algorithm Selector', Journal of Artificial Intelligence Research (JAIR), Vol. 53, pp. 745–778, 2015.",
    bullets_5=[
        "Algorithm selection pipelines involve complex design choices (feature pre-processing, model choice, hyperparameters, pre-solving budgets) that require manual expert tuning.",
        "Applied automated algorithm configuration (Sequential Model-based Algorithm Configuration, SMAC) to optimize the entire algorithm selection pipeline end-to-end for any given benchmark portfolio.",
        "Benchmarked across 13 diverse algorithm selection challenges from the ASlib repository covering SAT, Answer Set Programming (ASP), CSP, and QBF.",
        "Automatically configured selectors consistently matched or outperformed manually engineered, domain-specific state-of-the-art selection systems across every benchmark family.",
        "Emphasizes the necessity of disciplined hyperparameter control; OA-ASSP adopts this experimental rigor by freezing validation-tuned selector hyperparameters across all feature tiers to prevent confounding model capacity with feature utility."
    ]
)

# Paper 6: Bischl et al. (2016) - ASlib
build_paper_slide(
    prs, slide_idx=9, paper_num=6,
    short_title="Bischl et al. (2016) — ASlib: Algorithm Selection Benchmark Library",
    citation_info="Bernd Bischl et al., 'ASlib: A Benchmark Library for Algorithm Selection', Artificial Intelligence (AIJ), Vol. 237, pp. 41–58, 2016.",
    bullets_5=[
        "Proliferation of fragmented datasets, ad-hoc baselines, and inconsistent metrics prevented standardized comparisons and reproducible benchmarking in algorithm selection research.",
        "Established an open, comprehensive benchmark library with standardized data formats, train/validation/test splits, feature runtimes, solver runtimes, and baseline reference definitions.",
        "Assembled 17 comprehensive benchmark scenarios spanning constraint satisfaction, satisfiability, planning, and operations research contributed by multiple international research teams.",
        "Standardizing Single Best Solver (SBS), Virtual Best Solver (VBS), and Oracle Gap reference policies is essential for objectively quantifying how much available headroom an algorithm selector captures.",
        "Directly provides the formal reference framework (A_SBS, t(VBS), and OracleGap(Q)) that OA-ASSP builds upon to define performance headroom and derive the break-even metric RequiredCapture(Q)."
    ]
)

# Paper 7: Bast et al. (2016) - Route Planning
build_paper_slide(
    prs, slide_idx=10, paper_num=7,
    short_title="Bast et al. (2016) — Route Planning in Transportation Networks",
    citation_info="Hannah Bast, Daniel Delling, Andrew Goldberg, et al., 'Route Planning in Transportation Networks', Algorithm Engineering, LNCS Vol. 9220, Springer, pp. 19–80, 2016.",
    bullets_5=[
        "Computing exact point-to-point shortest paths on continental road networks and transit graphs with millions of nodes within interactive, sub-millisecond response budgets.",
        "Comprehensive synthesis of algorithm engineering techniques, surveying bidirectional search, goal-directed search (A*, ALT), and hierarchical preprocessing (Contraction Hierarchies, Hub Labeling, Transit Node Routing).",
        "Evaluated on continental-scale Western Europe and North America road networks comprising up to 18 million vertices and 42 million edges.",
        "Classical priority-queue Dijkstra is unacceptably slow for real-time queries; bidirectional and goal-directed variants achieve substantial speedups, while preprocessing yields microsecond query times.",
        "Establishes the real-world algorithm engineering foundation for exact shortest paths, providing the context for why canonical exact solvers execute in hundreds of microseconds and why selection overhead becomes a critical bottleneck."
    ]
)

# Paper 8: Kerschke et al. (2019) - Comprehensive Survey
build_paper_slide(
    prs, slide_idx=11, paper_num=8,
    short_title="Kerschke et al. (2019) — Automated Algorithm Selection Survey",
    citation_info="Pascal Kerschke, Holger H. Hoos, Frank Neumann, Heike Trautmann, 'Automated Algorithm Selection: Survey and Perspectives', Evolutionary Computation, Vol. 27, No. 1, MIT Press, pp. 3–45, 2019.",
    bullets_5=[
        "Synthesizing forty years of fragmented algorithm selection literature across discrete, continuous, combinatorial, and machine learning domains into a unified conceptual taxonomy.",
        "Developed a comprehensive survey classifying problem characteristics, feature extraction strategies, learning paradigms (regression, classification, ranking), and evaluation methodologies.",
        "Broad qualitative and quantitative synthesis spanning SAT, ASP, TSP, continuous black-box optimization, and machine learning meta-learning.",
        "While algorithm selection is widely successful, the computational overhead of computing instance features remains an acknowledged, persistent practical bottleneck that is frequently marginalized or ignored.",
        "Identifies feature computation cost as an open grand challenge in algorithm selection; OA-ASSP directly addresses this challenge by establishing an overhead-priced cost model that formally charges feature extraction and selector inference against available headroom."
    ]
)

# Paper 9: van der Blom & Vermetten (2026) - Feature Budgets
build_paper_slide(
    prs, slide_idx=12, paper_num=9,
    short_title="van der Blom & Vermetten (2026) — Feature Computation Budgets",
    citation_info="Koen van der Blom, Diederick Vermetten, 'On the Influence of the Feature Computation Budget on Per-Instance Algorithm Selection for Black-Box Optimization', arXiv:2605.04954, 2026.",
    bullets_5=[
        "Feature extraction in per-instance algorithm selection for black-box optimization (BBO) consumes expensive function evaluations directly from a strictly bounded total optimization budget.",
        "Systematically evaluated the trade-off of allocating varying fractions of a fixed evaluation budget to Exploratory Landscape Analysis (ELA) features across multiple algorithm portfolios and problem suites.",
        "Continuous black-box optimization benchmark suites (BBOB/COCO) evaluated across problem dimensions from 2D to 10D.",
        "Feature extraction is not free; allocating too large a budget fraction to features degrades net optimization quality, establishing that an optimal, problem-dependent feature budget exists.",
        "Shares OA-ASSP's core premise that characterization costs must be paid from solver savings, but operates in an internal sample-budget setting on isolated instances, whereas OA-ASSP investigates physical wall-clock latency across repeated queries where graph features amortize over workload size Q."
    ]
)

# Paper 10: Gholami Shiri et al. (IEEE CEC 2026) - Graph Landscapes
build_paper_slide(
    prs, slide_idx=13, paper_num=10,
    short_title="Gholami Shiri et al. (2026) — Graph Instance Landscapes",
    citation_info="Nemanja Gholami Shiri, Vladan Krminac, Bogdan Djukanović, et al., 'Graph Instance Landscapes: When Structural Similarity Does (Not) Reflect Shortest-Path Performance', Proc. IEEE CEC, arXiv:2606.18267, 2026.",
    bullets_5=[
        "Investigating whether structural similarity in low-cost graph feature space reflects the empirical runtime distributions of exact shortest-path algorithms.",
        "Embedded graph instances into a structural feature landscape, clustered instances into topological regions, and analyzed runtime distributions of four solvers: Dijkstra, Bidirectional Dijkstra, A*, and DEQ.",
        "Evaluated on weighted Erdős–Rényi random graphs, random geometric graphs, and real-world road network topologies.",
        "Solver performance varies significantly across graph topological regions, but structural feature similarity does not reliably translate to performance similarity, revealing complex algorithm-landscape boundaries.",
        "Represents the closest prior work by examining the same solver family (Dijkstra, Bidi Dijkstra, A*) and synthetic graph topologies, directly motivating OA-ASSP to investigate whether an actual selector can economically exploit this structural diversity to pay for its own decision overhead."
    ]
)

# =========================================================================
# SLIDE 14: COMPARISON TABLE (ALL 10 PAPERS)
# =========================================================================
slide14 = prs.slides.add_slide(blank_layout)
add_header(slide14, "Literature Comparison: Evolution of Algorithm Selection", "Synthesis & Taxonomy")

# Create table covering all 10 papers
rows, cols = 11, 6
table_shape = slide14.shapes.add_table(rows, cols, Inches(0.8), Inches(1.32), Inches(11.733), Inches(4.55))
table = table_shape.table

# Set Column Widths
table.columns[0].width = Inches(1.5)   # Paper & Year
table.columns[1].width = Inches(1.5)   # Problem Domain
table.columns[2].width = Inches(2.0)   # Portfolio / Solvers
table.columns[3].width = Inches(2.0)   # Features Used
table.columns[4].width = Inches(2.2)   # Overhead Accounting
table.columns[5].width = Inches(2.533) # Finding & Relation to OA-ASSP

table_data = [
    # Header
    ["Paper & Year", "Problem Domain", "Portfolio / Solvers", "Features Used", "Overhead Accounting", "Key Finding & Gap to OA-ASSP"],
    # Row 1
    ["Rice (1976)", "Mathematical Software", "Abstract Algorithm Portfolio", "Instance Characteristics", "Assumed negligible (zero cost)", "Foundational 4-space model; ignores feature and inference latency."],
    # Row 2
    ["Xu et al. (2008) [SATzilla]", "Propositional Satisfiability", "ZChaff, MiniSAT, March, etc.", "Syntactic formula features", "Charged against multi-second runs", "Huge gains on compute-heavy tasks; overhead absorbed by long runtimes."],
    # Row 3
    ["Hutter et al. (2014)", "SAT, MIP, TSP", "Exact & Stochastic Solvers", "Clause/matrix/graph stats", "Separated offline pre-computation", "Random forests predict runtime accurately; motivates regret-aware loss."],
    # Row 4
    ["Kotthoff (2014) [LLAMA]", "Combinatorial Optimization", "Generic user portfolios", "Domain-specific feature vectors", "Feature-cost filtering supported", "Standard modular toolkit; lacks fine-grained microsecond overhead tracking."],
    # Row 5
    ["Lindauer et al. (2015) [AutoFolio]", "ASlib Scenarios (SAT/ASP/QBF)", "Portfolio across 13 domains", "Automated feature selection", "Pre-solving schedule budgeted", "SMAC configures selectors; features treated as static instance properties."],
    # Row 6
    ["Bischl et al. (2016) [ASlib]", "Benchmarking Library", "17 Diverse Benchmark Scenarios", "Extensive domain features", "Recorded feature execution times", "Formalized SBS, VBS, and Oracle Gap baselines adopted by OA-ASSP."],
    # Row 7
    ["Bast et al. (2016)", "Road Network Routing", "Dijkstra, Bidi, A*, CH, TNR", "Network coordinates, hierarchy", "Query-time speedup focus", "Microsecond shortest-path solvers engineered; no adaptive selector evaluated."],
    # Row 8
    ["Kerschke et al. (2019)", "Algorithm Selection Survey", "Cross-domain review", "Taxonomy of problem features", "Identified as open practical barrier", "Definitive survey; flags feature computation costs as an unaddressed challenge."],
    # Row 9
    ["van der Blom (2026)", "Black-Box Optimization", "Continuous optimizers (CMA-ES)", "Exploratory Landscape Analysis", "Charged against function eval budget", "Analyzed feature budget trade-offs; lacks wall-clock and repeated-query model."],
    # Row 10
    ["Gholami Shiri (2026)", "Shortest Paths (Landscape)", "Dijkstra, Bidi, A*, DEQ", "Low-cost structural graph metrics", "No selection / No overhead charged", "Landscape clustering; motivates OA-ASSP's operational decision pricing."]
]

for r_idx, row_items in enumerate(table_data):
    for c_idx, cell_text in enumerate(row_items):
        cell = table.cell(r_idx, c_idx)
        cell.text = cell_text
        p = cell.text_frame.paragraphs[0]
        p.font.name = FONT_BODY
        p.alignment = PP_ALIGN.LEFT
        cell.margin_left = Inches(0.08)
        cell.margin_right = Inches(0.08)
        cell.margin_top = Inches(0.04)
        cell.margin_bottom = Inches(0.04)
        
        if r_idx == 0:
            p.font.name = FONT_HEADING
            p.font.bold = True
            p.font.size = Pt(9.5)
            p.font.color.rgb = COLOR_WHITE
            cell.fill.solid()
            cell.fill.fore_color.rgb = COLOR_PRIMARY_NAVY
        else:
            p.font.size = Pt(8.5)
            p.font.color.rgb = COLOR_DARK_TEXT
            cell.fill.solid()
            cell.fill.fore_color.rgb = COLOR_CARD_BG if r_idx % 2 == 1 else COLOR_WHITE

# Bottom Synthesis Card
synth_card = slide14.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.98), Inches(11.733), Inches(0.82))
set_shape_flat(synth_card, COLOR_RELEVANCE_BG, COLOR_RELEVANCE_BORDER, border_width=1.5)
tf_sc = synth_card.text_frame
tf_sc.vertical_anchor = MSO_ANCHOR.TOP
tf_sc.word_wrap = True
tf_sc.margin_left = Inches(0.2)
tf_sc.margin_top = Inches(0.08)
tf_sc.margin_right = Inches(0.2)

p_sct = tf_sc.paragraphs[0]
p_sct.text = "LITERATURE SYNTHESIS & RESEARCH PROGRESSION:"
p_sct.font.name = FONT_HEADING
p_sct.font.size = Pt(9)
p_sct.font.bold = True
p_sct.font.color.rgb = COLOR_SECONDARY_BLUE
p_sct.space_after = Pt(2)
p_sct.alignment = PP_ALIGN.LEFT

p_scb = tf_sc.add_paragraph()
p_scb.text = "Existing literature established portfolio value in multi-second domains (SATzilla, ASlib), identified feature budgets in continuous optimization (van der Blom), and mapped shortest-path landscapes (Gholami Shiri). However, NO prior work prices physical wall-clock selection cost against SBS–VBS headroom across repeated query workloads (Q) on resident graphs — defining the exact gap addressed by OA-ASSP."
p_scb.font.name = FONT_BODY
p_scb.font.size = Pt(9)
p_scb.font.color.rgb = COLOR_DARK_TEXT
p_scb.alignment = PP_ALIGN.LEFT

add_footer(slide14, 14)

# =========================================================================
# SLIDE 15: OA-ASSP ARCHITECTURE / CLASSIFICATION / BLOCK DIAGRAM
# =========================================================================
slide15 = prs.slides.add_slide(blank_layout)
add_header(slide15, "OA-ASSP System Architecture & Evaluation Framework", "Methodological Architecture")

# Section 1 Header (Pipeline)
s1_lbl = slide15.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(11.733), Inches(0.28))
tf_s1 = s1_lbl.text_frame
tf_s1.margin_left = tf_s1.margin_top = tf_s1.margin_right = tf_s1.margin_bottom = 0
p = tf_s1.paragraphs[0]
p.text = "ONLINE ADAPTIVE SELECTION PIPELINE (COST COMPOSITION)"
p.font.name = FONT_HEADING
p.font.size = Pt(10.5)
p.font.bold = True
p.font.color.rgb = COLOR_SECONDARY_BLUE
p.alignment = PP_ALIGN.LEFT

# Pipeline Step 1: Input
b1 = slide15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.62), Inches(2.65), Inches(2.15))
set_shape_flat(b1, COLOR_WHITE, COLOR_SECONDARY_BLUE)
tf1 = b1.text_frame
tf1.vertical_anchor = MSO_ANCHOR.TOP
tf1.word_wrap = True
tf1.margin_left = tf1.margin_right = Inches(0.14)
tf1.margin_top = Inches(0.12)
p1 = tf1.paragraphs[0]
p1.text = "1. Workload Inputs"
p1.font.name = FONT_HEADING
p1.font.size = Pt(11)
p1.font.bold = True
p1.font.color.rgb = COLOR_PRIMARY_NAVY
p1.space_after = Pt(4)
p1.alignment = PP_ALIGN.LEFT
p1b = tf1.add_paragraph()
p1b.text = "• Resident Graph G=(V,E,w)\n• Query Workload Q: {(s, t)}\n• Q ∈ {1, 10, 50, 100, 500}\n• Deterministic query sequence"
p1b.font.name = FONT_BODY
p1b.font.size = Pt(9.5)
p1b.font.color.rgb = COLOR_BODY_TEXT
p1b.alignment = PP_ALIGN.LEFT

# Pipeline Step 2: Features
b2 = slide15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(3.8), Inches(1.62), Inches(2.75), Inches(2.15))
set_shape_flat(b2, COLOR_WHITE, COLOR_SECONDARY_BLUE)
tf2 = b2.text_frame
tf2.vertical_anchor = MSO_ANCHOR.TOP
tf2.word_wrap = True
tf2.margin_left = tf2.margin_right = Inches(0.14)
tf2.margin_top = Inches(0.12)
p2 = tf2.paragraphs[0]
p2.text = "2. Feature Extraction"
p2.font.name = FONT_HEADING
p2.font.size = Pt(11)
p2.font.bold = True
p2.font.color.rgb = COLOR_PRIMARY_NAVY
p2.space_after = Pt(4)
p2.alignment = PP_ALIGN.LEFT
p2b = tf2.add_paragraph()
p2b.text = "• Graph Features: C_graph (once)\n• Query Features: C_query (per query)\n• Feature Assembly: C_vec\n• Tiers: Tier 0 (6), Tier 1 (21, primary), Tier 2 (23)"
p2b.font.name = FONT_BODY
p2b.font.size = Pt(9.5)
p2b.font.color.rgb = COLOR_BODY_TEXT
p2b.alignment = PP_ALIGN.LEFT

# Pipeline Step 3: Selector
b3 = slide15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.9), Inches(1.62), Inches(2.75), Inches(2.15))
set_shape_flat(b3, COLOR_WHITE, COLOR_SECONDARY_BLUE)
tf3 = b3.text_frame
tf3.vertical_anchor = MSO_ANCHOR.TOP
tf3.word_wrap = True
tf3.margin_left = tf3.margin_right = Inches(0.14)
tf3.margin_top = Inches(0.12)
p3 = tf3.paragraphs[0]
p3.text = "3. Selector Inference"
p3.font.name = FONT_HEADING
p3.font.size = Pt(11)
p3.font.bold = True
p3.font.color.rgb = COLOR_PRIMARY_NAVY
p3.space_after = Pt(4)
p3.alignment = PP_ALIGN.LEFT
p3b = tf3.add_paragraph()
p3b.text = "• Decision Tree (depth 6, leaf 3)\n• Library Mode: 87.9 µs/query (scikit-learn single-row)\n• Compiled Mode: 0.8 µs/query (native branches, ~110× faster)"
p3b.font.name = FONT_BODY
p3b.font.size = Pt(9.5)
p3b.font.color.rgb = COLOR_BODY_TEXT
p3b.alignment = PP_ALIGN.LEFT

# Pipeline Step 4: Solvers
b4 = slide15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(10.0), Inches(1.62), Inches(2.533), Inches(2.15))
set_shape_flat(b4, COLOR_WHITE, COLOR_SECONDARY_BLUE)
tf4 = b4.text_frame
tf4.vertical_anchor = MSO_ANCHOR.TOP
tf4.word_wrap = True
tf4.margin_left = tf4.margin_right = Inches(0.14)
tf4.margin_top = Inches(0.12)
p4 = tf4.paragraphs[0]
p4.text = "4. Solver Execution"
p4.font.name = FONT_HEADING
p4.font.size = Pt(11)
p4.font.bold = True
p4.font.color.rgb = COLOR_PRIMARY_NAVY
p4.space_after = Pt(4)
p4.alignment = PP_ALIGN.LEFT
p4b = tf4.add_paragraph()
p4b.text = "• Dispatched Solver:\n  - Dijkstra (Isotropic)\n  - Bidirectional Dijkstra\n  - A* (Geometric only)\n• Evaluates exact shortest path"
p4b.font.name = FONT_BODY
p4b.font.size = Pt(9.5)
p4b.font.color.rgb = COLOR_BODY_TEXT
p4b.alignment = PP_ALIGN.LEFT

# Arrows between pipeline steps
for arr_x in [Inches(3.5), Inches(6.6), Inches(9.7)]:
    arr = slide15.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, arr_x, Inches(2.5), Inches(0.25), Inches(0.3))
    set_shape_flat(arr, COLOR_MUTED_TEXT)

# Section 2 Header (Framework)
s2_lbl = slide15.shapes.add_textbox(Inches(0.8), Inches(3.9), Inches(11.733), Inches(0.28))
tf_s2 = s2_lbl.text_frame
tf_s2.margin_left = tf_s2.margin_top = tf_s2.margin_right = tf_s2.margin_bottom = 0
p = tf_s2.paragraphs[0]
p.text = "OVERHEAD-AWARE ECONOMIC EVALUATION FRAMEWORK"
p.font.name = FONT_HEADING
p.font.size = Pt(10.5)
p.font.bold = True
p.font.color.rgb = COLOR_SECONDARY_BLUE
p.alignment = PP_ALIGN.LEFT

# Four Evaluation Cards
ec_w = 2.7
ec_gap = 0.28
ec_y = 4.22
ec_h = 2.55

# Card A: Reference Baselines
ca = slide15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(ec_y), Inches(ec_w), Inches(ec_h))
set_shape_flat(ca, COLOR_CARD_BG, COLOR_CARD_BORDER)
tfa = ca.text_frame
tfa.vertical_anchor = MSO_ANCHOR.TOP
tfa.word_wrap = True
tfa.margin_left = tfa.margin_right = Inches(0.14)
tfa.margin_top = Inches(0.12)
pa = tfa.paragraphs[0]
pa.text = "A. Reference Baselines"
pa.font.name = FONT_HEADING
pa.font.size = Pt(11)
pa.font.bold = True
pa.font.color.rgb = COLOR_PRIMARY_NAVY
pa.space_after = Pt(4)
pa.alignment = PP_ALIGN.LEFT
pab = tfa.add_paragraph()
pab.text = "• SBS (Training-Only):\n  Always-Bidirectional-Dijkstra\n  SBS Cost = 1064.20 ms\n• VBS (Oracle Lower Bound):\n  VBS Cost = 941.68 ms\n• Oracle Gap (Headroom):\n  122.52 ms (11.51% of SBS)"
pab.font.name = FONT_BODY
pab.font.size = Pt(9.5)
pab.font.color.rgb = COLOR_BODY_TEXT
pab.alignment = PP_ALIGN.LEFT

# Card B: Overhead Accounting
cb = slide15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8 + ec_w + ec_gap), Inches(ec_y), Inches(ec_w), Inches(ec_h))
set_shape_flat(cb, COLOR_CARD_BG, COLOR_CARD_BORDER)
tfb = cb.text_frame
tfb.vertical_anchor = MSO_ANCHOR.TOP
tfb.word_wrap = True
tfb.margin_left = tfb.margin_right = Inches(0.14)
tfb.margin_top = Inches(0.12)
pb = tfb.paragraphs[0]
pb.text = "B. Selection Overhead"
pb.font.name = FONT_HEADING
pb.font.size = Pt(11)
pb.font.bold = True
pb.font.color.rgb = COLOR_PRIMARY_NAVY
pb.space_after = Pt(4)
pb.alignment = PP_ALIGN.LEFT
pbb = tfb.add_paragraph()
pbb.text = "• Library Overhead:\n  472.04 ms (at Q=500)\n  (8.5 ms graph + 463.6 ms query)\n• Compiled Overhead:\n  35.51 ms (at Q=500)\n  (8.5 ms graph + 27.0 ms query)\n• 13.3× total overhead drop"
pbb.font.name = FONT_BODY
pbb.font.size = Pt(9.5)
pbb.font.color.rgb = COLOR_BODY_TEXT
pbb.alignment = PP_ALIGN.LEFT

# Card C: Accounting Metrics
cc = slide15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8 + 2*(ec_w + ec_gap)), Inches(ec_y), Inches(ec_w), Inches(ec_h))
set_shape_flat(cc, COLOR_CARD_BG, COLOR_CARD_BORDER)
tfc = cc.text_frame
tfc.vertical_anchor = MSO_ANCHOR.TOP
tfc.word_wrap = True
tfc.margin_left = tfc.margin_right = Inches(0.14)
tfc.margin_top = Inches(0.12)
pc = tfc.paragraphs[0]
pc.text = "C. Decision Metrics"
pc.font.name = FONT_HEADING
pc.font.size = Pt(11)
pc.font.bold = True
pc.font.color.rgb = COLOR_PRIMARY_NAVY
pc.space_after = Pt(4)
pc.alignment = PP_ALIGN.LEFT
pcb = tfc.add_paragraph()
pcb.text = "• RequiredCapture(Q):\n  Overhead(Q) / OracleGap(Q)\n• SolverOnlyCapture(Q):\n  (SBS - Chosen) / OracleGap\n• Operative Condition:\n  SolverOnlyCapture > ReqCapture\n  (Separates overhead from quality)"
pcb.font.name = FONT_BODY
pcb.font.size = Pt(9.5)
pcb.font.color.rgb = COLOR_BODY_TEXT
pcb.alignment = PP_ALIGN.LEFT

# Card D: Dual Bottleneck Outcome
cd = slide15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8 + 3*(ec_w + ec_gap)), Inches(ec_y), Inches(ec_w), Inches(ec_h))
set_shape_flat(cd, COLOR_WHITE, COLOR_SECONDARY_BLUE, border_width=1.5)
tfd = cd.text_frame
tfd.vertical_anchor = MSO_ANCHOR.TOP
tfd.word_wrap = True
tfd.margin_left = tfd.margin_right = Inches(0.14)
tfd.margin_top = Inches(0.12)
pd = tfd.paragraphs[0]
pd.text = "D. Empirical Verdict"
pd.font.name = FONT_HEADING
pd.font.size = Pt(11)
pd.font.bold = True
pd.font.color.rgb = COLOR_PRIMARY_NAVY
pd.space_after = Pt(4)
pd.alignment = PP_ALIGN.LEFT
pdb = tfd.add_paragraph()
pdb.text = "• Library: ReqCap = 3.8527 > 1.0\n  Strictly OVERHEAD-BOUND\n• Compiled: ReqCap = 0.2898 < 1.0\n  Affordable, but SolverOnlyCap\n  = -0.1633 (EFFICACY-BOUND)\n• Genuine Crossovers: 0 / 40\n  (Noise floor: 16.3% lib / 9.4% cmp)"
pdb.font.name = FONT_BODY
pdb.font.size = Pt(9.5)
pdb.font.color.rgb = COLOR_DARK_TEXT
pdb.alignment = PP_ALIGN.LEFT

add_footer(slide15, 15)

# =========================================================================
# SLIDE 16: RESEARCH GAP AND FUTURE WORK
# =========================================================================
slide16 = prs.slides.add_slide(blank_layout)
add_header(slide16, "Research Gap & Future Research Directions", "Research Synthesis")

# Left Panel: Research Gap (Width: 5.7")
gap_card = slide16.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.35), Inches(5.7), Inches(5.4))
set_shape_flat(gap_card, COLOR_WHITE, COLOR_CARD_BORDER)
tfg = gap_card.text_frame
tfg.vertical_anchor = MSO_ANCHOR.TOP
tfg.word_wrap = True
tfg.margin_left = tfg.margin_right = Inches(0.25)
tfg.margin_top = Inches(0.2)

pg = tfg.paragraphs[0]
pg.text = "RESEARCH GAP IDENTIFIED BY SURVEY"
pg.font.name = FONT_HEADING
pg.font.size = Pt(13)
pg.font.bold = True
pg.font.color.rgb = COLOR_PRIMARY_NAVY
pg.space_after = Pt(12)
pg.alignment = PP_ALIGN.LEFT

gaps = [
    ("1. Microsecond Scale Disconnect:", " Prior selection literature (SATzilla, ASlib) assumes feature extraction is negligible compared to multi-second runs. In exact shortest paths (V ≤ 320), solver runtimes finish in hundreds of microseconds, where selection latency rivals execution time."),
    ("2. Physical Wall-Clock Accounting Gap:", " Feature-cost studies in optimization (e.g. van der Blom & Vermetten) charge abstract sample budgets. No prior research measured end-to-end physical wall-clock extraction, vector assembly, and inference in an active graph query loop."),
    ("3. Workload Amortization Dimension (Q):", " Prior work evaluates instances in isolation. Real shortest-path applications query persistent graphs, requiring an explicit workload axis (Q ∈ {1...500}) to quantify the amortization of one-time graph metrics against recurring query costs."),
    ("4. Headroom-Debited Economic Viability:", " Existing shortest-path landscape studies (e.g. Gholami Shiri et al.) stop at clustering. The vital question of whether an adaptive selector can capture enough SBS–VBS headroom to earn back its overhead remained unmeasured.")
]

for g_title, g_desc in gaps:
    p_row = tfg.add_paragraph()
    p_row.text = "• "
    p_row.font.name = FONT_BODY
    p_row.font.size = Pt(10.5)
    p_row.font.color.rgb = COLOR_SECONDARY_BLUE
    p_row.space_after = Pt(8)
    p_row.alignment = PP_ALIGN.LEFT
    
    r1 = p_row.add_run()
    r1.text = f"{g_title} "
    r1.font.bold = True
    r1.font.color.rgb = COLOR_DARK_TEXT
    
    r2 = p_row.add_run()
    r2.text = g_desc
    r2.font.bold = False
    r2.font.color.rgb = COLOR_BODY_TEXT

# Right Panel: Future Work (Width: 5.7")
fut_card = slide16.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.833), Inches(1.35), Inches(5.7), Inches(5.4))
set_shape_flat(fut_card, COLOR_CARD_BG, COLOR_SECONDARY_BLUE, border_width=1.5)
tff = fut_card.text_frame
tff.vertical_anchor = MSO_ANCHOR.TOP
tff.word_wrap = True
tff.margin_left = tff.margin_right = Inches(0.25)
tff.margin_top = Inches(0.2)

pf = tff.paragraphs[0]
pf.text = "DEFENSIBLE FUTURE WORK (FROM PAPER)"
pf.font.name = FONT_HEADING
pf.font.size = Pt(13)
pf.font.bold = True
pf.font.color.rgb = COLOR_PRIMARY_NAVY
pf.space_after = Pt(12)
pf.alignment = PP_ALIGN.LEFT

future_items = [
    ("1. Runtime-Regret-Aware Objectives:", " Replace unweighted 0/1 classification loss with loss functions directly weighted by runtime regret (t(A) - t(VBS)), severely penalizing catastrophic mispredictions over trivial differences."),
    ("2. Cost-Sensitive / Utility-Aware Selection:", " Formulate decision thresholds requiring predicted solver runtime savings to strictly exceed marginal per-query decision overhead before switching away from the fixed baseline."),
    ("3. Direct Runtime Prediction Models:", " Train regression architectures (random forests or gradient boosting, Hutter et al. style) to predict continuous execution latencies for each solver independently."),
    ("4. Scale & Topology Expansion:", " Benchmark large-scale networks (V >> 320) and real-world road/transit graphs where solver runtimes expand, potentially widening available oracle headroom."),
    ("5. Preprocessing-Based Solvers:", " Incorporate advanced algorithm-engineering solvers (Contraction Hierarchies, Hub Labeling, ALT) into the portfolio to evaluate selection across hierarchical routing engines.")
]

for f_title, f_desc in future_items:
    p_row = tff.add_paragraph()
    p_row.text = "▶ "
    p_row.font.name = FONT_BODY
    p_row.font.size = Pt(10.5)
    p_row.font.color.rgb = COLOR_ACCENT_AMBER
    p_row.space_after = Pt(7)
    p_row.alignment = PP_ALIGN.LEFT
    
    r1 = p_row.add_run()
    r1.text = f"{f_title} "
    r1.font.bold = True
    r1.font.color.rgb = COLOR_DARK_TEXT
    
    r2 = p_row.add_run()
    r2.text = f_desc
    r2.font.bold = False
    r2.font.color.rgb = COLOR_BODY_TEXT

p_warn = tff.add_paragraph()
p_warn.text = "Note: The above directions represent defensible research hypotheses motivated by OA-ASSP's empirical findings, not pre-existing validated interventions."
p_warn.font.name = FONT_BODY
p_warn.font.size = Pt(8.5)
p_warn.font.italic = True
p_warn.font.color.rgb = COLOR_MUTED_TEXT
p_warn.alignment = PP_ALIGN.LEFT

add_footer(slide16, 16)

# =========================================================================
# SLIDE 17: CONCLUSION
# =========================================================================
slide17 = prs.slides.add_slide(blank_layout)
add_header(slide17, "Conclusion: Findings, Implications & Guiding Principle", "Academic Conclusion")

# Top Container: Key Findings Cards (2 Columns)
c1 = slide17.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.35), Inches(5.7), Inches(4.0))
set_shape_flat(c1, COLOR_WHITE, COLOR_CARD_BORDER)
tf_c1 = c1.text_frame
tf_c1.vertical_anchor = MSO_ANCHOR.TOP
tf_c1.word_wrap = True
tf_c1.margin_left = tf_c1.margin_right = Inches(0.25)
tf_c1.margin_top = Inches(0.18)

p_c1h = tf_c1.paragraphs[0]
p_c1h.text = "CORE EMPIRICAL FINDINGS"
p_c1h.font.name = FONT_HEADING
p_c1h.font.size = Pt(12)
p_c1h.font.bold = True
p_c1h.font.color.rgb = COLOR_PRIMARY_NAVY
p_c1h.space_after = Pt(10)
p_c1h.alignment = PP_ALIGN.LEFT

findings_1 = [
    ("Exploitable Complementarity Exists:", " On geometric graphs, A* wins 6%–20% of queries, Dijkstra 23%–50%, and Bidirectional Dijkstra 38%–67%, confirming genuine algorithmic diversity exists to be exploited."),
    ("Library Mode is Overhead-Bound:", " Standard scikit-learn single-row inference incurs 87.9 µs per query (RequiredCapture = 3.8527 > 1.0), consuming nearly 4× the entire oracle gap and rendering break-even impossible."),
    ("Native Compilation Eliminates Overhead:", " Compiling the decision tree to native conditional branches achieves an ~110× latency reduction (0.8 µs per query), bringing RequiredCapture down to 0.2898 (well within the viable zone).")
]

for title_f, desc_f in findings_1:
    pf_row = tf_c1.add_paragraph()
    pf_row.text = "• "
    pf_row.font.name = FONT_BODY
    pf_row.font.size = Pt(10.5)
    pf_row.font.color.rgb = COLOR_SECONDARY_BLUE
    pf_row.space_after = Pt(7)
    pf_row.alignment = PP_ALIGN.LEFT
    
    r1 = pf_row.add_run()
    r1.text = f"{title_f} "
    r1.font.bold = True
    r1.font.color.rgb = COLOR_DARK_TEXT
    
    r2 = pf_row.add_run()
    r2.text = desc_f
    r2.font.bold = False
    r2.font.color.rgb = COLOR_BODY_TEXT

c2 = slide17.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.833), Inches(1.35), Inches(5.7), Inches(4.0))
set_shape_flat(c2, COLOR_WHITE, COLOR_CARD_BORDER)
tf_c2 = c2.text_frame
tf_c2.vertical_anchor = MSO_ANCHOR.TOP
tf_c2.word_wrap = True
tf_c2.margin_left = tf_c2.margin_right = Inches(0.25)
tf_c2.margin_top = Inches(0.18)

p_c2h = tf_c2.paragraphs[0]
p_c2h.text = "DECISION QUALITY & METHODOLOGICAL LESSONS"
p_c2h.font.name = FONT_HEADING
p_c2h.font.size = Pt(12)
p_c2h.font.bold = True
p_c2h.font.color.rgb = COLOR_PRIMARY_NAVY
p_c2h.space_after = Pt(10)
p_c2h.alignment = PP_ALIGN.LEFT

findings_2 = [
    ("Objective Function Bottleneck:", " Even when overhead is removed, unweighted 0/1 classification loss fails to convert complementarity into runtime savings (SolverOnlyCapture = -0.1633), collapsing toward the majority policy."),
    ("Zero Genuine Crossovers:", " After qualifying nominal runtime differences against empirical measurement dispersion (16.32% library, 9.40% compiled), adaptive selection achieves exactly 0 out of 40 genuine crossover cells."),
    ("Scientific Claim Boundaries:", " OA-ASSP does not claim selection is universally non-viable; rather, it establishes that per-instance selection must be formally evaluated against the headroom it is meant to exploit.")
]

for title_f, desc_f in findings_2:
    pf_row = tf_c2.add_paragraph()
    pf_row.text = "• "
    pf_row.font.name = FONT_BODY
    pf_row.font.size = Pt(10.5)
    pf_row.font.color.rgb = COLOR_SECONDARY_BLUE
    pf_row.space_after = Pt(7)
    pf_row.alignment = PP_ALIGN.LEFT
    
    r1 = pf_row.add_run()
    r1.text = f"{title_f} "
    r1.font.bold = True
    r1.font.color.rgb = COLOR_DARK_TEXT
    
    r2 = pf_row.add_run()
    r2.text = desc_f
    r2.font.bold = False
    r2.font.color.rgb = COLOR_BODY_TEXT

# Bottom Hero Quote Card
quote_card = slide17.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.5), Inches(11.733), Inches(1.25))
set_shape_flat(quote_card, COLOR_PRIMARY_NAVY, COLOR_SECONDARY_BLUE, border_width=1.5)
tf_q = quote_card.text_frame
tf_q.vertical_anchor = MSO_ANCHOR.TOP
tf_q.word_wrap = True
tf_q.margin_left = tf_q.margin_right = Inches(0.3)
tf_q.margin_top = Inches(0.18)

p_ql = tf_q.paragraphs[0]
p_ql.text = "CORE GUIDING PRINCIPLE FOR EMPIRICAL ALGORITHMICS:"
p_ql.font.name = FONT_HEADING
p_ql.font.size = Pt(10)
p_ql.font.bold = True
p_ql.font.color.rgb = COLOR_SECONDARY_BLUE
p_ql.space_after = Pt(4)
p_ql.alignment = PP_ALIGN.CENTER

p_qm = tf_q.add_paragraph()
p_qm.text = '"The central question is not only which solver is best, but whether the cost of choosing it can be justified by the workload."'
p_qm.font.name = FONT_BODY
p_qm.font.size = Pt(14)
p_qm.font.bold = True
p_qm.font.color.rgb = COLOR_WHITE
p_qm.alignment = PP_ALIGN.CENTER

add_footer(slide17, 17)

# -------------------------------------------------------------------------
# SAVE PRESENTATION
# -------------------------------------------------------------------------
output_path = Path("OA_ASSP_DAA_DA1_Presentation.pptx").resolve()
prs.save(str(output_path))
print(f"Refined presentation generated successfully: {output_path}")
print(f"Total slides: {len(prs.slides)}")
