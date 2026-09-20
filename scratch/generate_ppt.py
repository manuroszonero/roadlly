import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    # Color Palette
    COLOR_BG = RGBColor(13, 13, 17)        # #0d0d11
    COLOR_CARD = RGBColor(22, 22, 28)      # #16161c
    COLOR_BORDER = RGBColor(45, 45, 55)    # #2d2d37
    COLOR_WHITE = RGBColor(255, 255, 255)  # #ffffff
    COLOR_MUTED = RGBColor(161, 161, 170)  # #a1a1aa
    COLOR_ACCENT = RGBColor(220, 220, 230) # #dcdce6
    COLOR_LINE = RGBColor(80, 80, 95)
    
    blank_layout = prs.slide_layouts[6]
    
    slides_data = [
        {
            "slide_type": "title",
            "title": "ROADLYY",
            "subtitle": "Urban Traffic Intelligence & Multi-Horizon Spatial-Temporal ML Engine",
            "domain": "Domain: AI in Smart Cities & Urban Mobility",
            "team": "Team: Culers",
            "tagline": "End-to-End Predictive Traffic Analytics, Graph Shockwaves & Detour Optimization"
        },
        {
            "slide_type": "content",
            "title": "1. The Urban Gridlock Problem",
            "subtitle": "Non-Linear Congestion & Cascading Shockwave Bottlenecks",
            "cards": [
                {
                    "heading": "Reactive, Not Predictive",
                    "text": "Current navigation systems and traffic centers only detect congestion after it has already formed, causing massive driver delays."
                },
                {
                    "heading": "Upstream Spillover Shockwaves",
                    "text": "A single lane blockage or crash does not stay isolated. Queues spill backward, creating compounding gridlock across feeder links."
                },
                {
                    "heading": "Lack of ROI-Driven Planning",
                    "text": "Municipalities lack data-driven decision frameworks to quantify which infrastructure upgrades yield the highest delay reductions."
                }
            ]
        },
        {
            "slide_type": "content",
            "title": "2. Roadlyy Solution Architecture",
            "subtitle": "High-Throughput End-to-End Intelligence Pipeline",
            "cards": [
                {
                    "heading": "1. Graph Ingestion Core",
                    "text": "Directed urban road graph (NetworkX) modeling 436 links and 120 nodes with physical lane capacities and speed limits."
                },
                {
                    "heading": "2. Multi-Horizon ML Models",
                    "text": "HistGradientBoosting regressors trained on 1.88M+ rows predicting Speed, Flow, and Congestion across +15m, +30m, +45m, and +60m."
                },
                {
                    "heading": "3. Interactive Command Center",
                    "text": "Sub-millisecond FastAPI REST API powering a dark-monochrome Leaflet geospatial operations dashboard."
                }
            ]
        },
        {
            "slide_type": "content",
            "title": "3. Metropolitan Graph & Dataset Scale",
            "subtitle": "High-Fidelity Spatial-Temporal Telemetry Across 19 Continuous Days",
            "cards": [
                {
                    "heading": "1.88M+ Observations",
                    "text": "Trained and validated on 1,884,960 records with 5-minute granular velocity, flow volume (vph), and density indices."
                },
                {
                    "heading": "436 Road Links & 120 Nodes",
                    "text": "Models Hyderabad metropolitan core across Motorways (60 km/h), Arterials (50 km/h), Collectors (40 km/h), and Local streets."
                },
                {
                    "heading": "BPR Physics & Weather Friction",
                    "text": "Integrates Bureau of Public Roads (BPR) speed-flow-density curves with real-time temperature and rainfall intensity (mm/h)."
                }
            ]
        },
        {
            "slide_type": "metrics",
            "title": "4. Multi-Horizon AI Forecasting Engine",
            "subtitle": "Validated Accuracy Across 481,344 Targets (HistGradientBoosting)",
            "metrics": [
                {"horizon": "+15 min", "r2": "91.0% R²", "mae": "MAE: 2.38 km/h", "desc": "Tactical immediate forecasting"},
                {"horizon": "+30 min", "r2": "89.2% R²", "mae": "MAE: 2.85 km/h", "desc": "Short-term trend projection"},
                {"horizon": "+45 min", "r2": "87.4% R²", "mae": "MAE: 3.12 km/h", "desc": "Medium-range buildup alert"},
                {"horizon": "+60 min", "r2": "85.8% R²", "mae": "MAE: 3.45 km/h", "desc": "1-Hour strategic horizon"}
            ]
        },
        {
            "slide_type": "content",
            "title": "5. Shockwave Propagation & Dynamic Detours",
            "subtitle": "Graph-Aware Spillover Mitigation & Automated Rerouting",
            "cards": [
                {
                    "heading": "Topological Feeder Analysis",
                    "text": "When a corridor is disrupted, the graph engine traces upstream in-edges to compute spillback speed drops and queue accumulation."
                },
                {
                    "heading": "Dynamic Detour Routing",
                    "text": "Computes the optimal alternative shortest sub-graph path bypassing the incident link with exact detour length and added travel time penalty."
                },
                {
                    "heading": "Incident Pulse Beacons",
                    "text": "High-contrast visual hierarchy: White incident beacon (!), silver upstream feeder alerts, and dashed white detour route lines."
                }
            ]
        },
        {
            "slide_type": "content",
            "title": "6. What-If Sandbox & Capital Planning",
            "subtitle": "Interactive Scenario Evaluator & 90-Candidate ROI Matrix",
            "cards": [
                {
                    "heading": "Live Test Case Evaluator",
                    "text": "Injects custom lane blockages, accidents, or storms on any link. Normalizes inputs (4 -> R0004) with dynamic physics synthesis."
                },
                {
                    "heading": "90 Planning Candidates",
                    "text": "Evaluates Lane Additions, Capacity Upgrades, Turn Lanes, Signal Retiming, and Connectors for city authorities."
                },
                {
                    "heading": "Quantitative ROI Score",
                    "text": "Ranked by Weekly Vehicle Delay Hours Saved per Unit Cost Index (ROI = Delay Hours / Cost Index)."
                }
            ]
        },
        {
            "slide_type": "title",
            "title": "ROADLYY — Smart City Impact",
            "subtitle": "Predictive. Graph-Aware. Production-Ready.",
            "domain": "Domain: AI in Smart Cities | Team: Culers",
            "team": "GitHub Repository: https://github.com/manuroszonero/roadlly",
            "tagline": "Transforming Metropolitan Traffic Management from Firefighting to Foresight"
        }
    ]
    
    for s_idx, data in enumerate(slides_data):
        slide = prs.slides.add_slide(blank_layout)
        
        # Background
        bg_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg_shape.fill.solid()
        bg_shape.fill.fore_color.rgb = COLOR_BG
        bg_shape.line.fill.background()
        
        if data["slide_type"] == "title":
            # Outer Card
            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.5), Inches(1.0), Inches(10.333), Inches(5.5))
            card.fill.solid()
            card.fill.fore_color.rgb = COLOR_CARD
            card.line.color.rgb = COLOR_BORDER
            card.line.width = Pt(1.5)
            
            # Title Box
            tx_box = slide.shapes.add_textbox(Inches(2.0), Inches(1.4), Inches(9.333), Inches(1.8))
            tf = tx_box.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = data["title"]
            p.alignment = PP_ALIGN.CENTER
            p.font.name = 'Arial'
            p.font.size = Pt(44)
            p.font.bold = True
            p.font.color.rgb = COLOR_WHITE
            
            # Subtitle Box
            tx_sub = slide.shapes.add_textbox(Inches(2.0), Inches(2.8), Inches(9.333), Inches(1.0))
            tf_sub = tx_sub.text_frame
            tf_sub.word_wrap = True
            p_sub = tf_sub.paragraphs[0]
            p_sub.text = data["subtitle"]
            p_sub.alignment = PP_ALIGN.CENTER
            p_sub.font.name = 'Arial'
            p_sub.font.size = Pt(18)
            p_sub.font.color.rgb = COLOR_MUTED
            
            # Domain & Team Box
            tx_info = slide.shapes.add_textbox(Inches(2.0), Inches(3.9), Inches(9.333), Inches(1.2))
            tf_info = tx_info.text_frame
            tf_info.word_wrap = True
            p_dom = tf_info.paragraphs[0]
            p_dom.text = data["domain"]
            p_dom.alignment = PP_ALIGN.CENTER
            p_dom.font.name = 'Arial'
            p_dom.font.size = Pt(16)
            p_dom.font.bold = True
            p_dom.font.color.rgb = COLOR_WHITE
            
            p_team = tf_info.add_paragraph()
            p_team.text = data["team"]
            p_team.alignment = PP_ALIGN.CENTER
            p_team.font.name = 'Arial'
            p_team.font.size = Pt(15)
            p_team.font.color.rgb = COLOR_MUTED
            
            p_tag = tf_info.add_paragraph()
            p_tag.text = data["tagline"]
            p_tag.alignment = PP_ALIGN.CENTER
            p_tag.font.name = 'Arial'
            p_tag.font.size = Pt(13)
            p_tag.font.color.rgb = COLOR_LINE
            
        elif data["slide_type"] == "content":
            # Header
            tx_header = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.733), Inches(1.2))
            tf_h = tx_header.text_frame
            tf_h.word_wrap = True
            p_h = tf_h.paragraphs[0]
            p_h.text = data["title"]
            p_h.font.name = 'Arial'
            p_h.font.size = Pt(28)
            p_h.font.bold = True
            p_h.font.color.rgb = COLOR_WHITE
            
            p_sub = tf_h.add_paragraph()
            p_sub.text = data["subtitle"]
            p_sub.font.name = 'Arial'
            p_sub.font.size = Pt(14)
            p_sub.font.color.rgb = COLOR_MUTED
            
            # 3 Cards
            card_w = Inches(3.64)
            card_h = Inches(4.8)
            card_y = Inches(1.8)
            spacing = Inches(0.4)
            
            for c_idx, card_info in enumerate(data["cards"]):
                card_x = Inches(0.8) + c_idx * (card_w + spacing)
                c_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, card_x, card_y, card_w, card_h)
                c_shape.fill.solid()
                c_shape.fill.fore_color.rgb = COLOR_CARD
                c_shape.line.color.rgb = COLOR_BORDER
                c_shape.line.width = Pt(1.2)
                
                tb = slide.shapes.add_textbox(card_x + Inches(0.25), card_y + Inches(0.3), card_w - Inches(0.5), card_h - Inches(0.6))
                tf_c = tb.text_frame
                tf_c.word_wrap = True
                
                p_hd = tf_c.paragraphs[0]
                p_hd.text = card_info["heading"]
                p_hd.font.name = 'Arial'
                p_hd.font.size = Pt(18)
                p_hd.font.bold = True
                p_hd.font.color.rgb = COLOR_WHITE
                
                p_tx = tf_c.add_paragraph()
                p_tx.text = "\n" + card_info["text"]
                p_tx.font.name = 'Arial'
                p_tx.font.size = Pt(13.5)
                p_tx.font.color.rgb = COLOR_MUTED
                
        elif data["slide_type"] == "metrics":
            # Header
            tx_header = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.733), Inches(1.2))
            tf_h = tx_header.text_frame
            tf_h.word_wrap = True
            p_h = tf_h.paragraphs[0]
            p_h.text = data["title"]
            p_h.font.name = 'Arial'
            p_h.font.size = Pt(28)
            p_h.font.bold = True
            p_h.font.color.rgb = COLOR_WHITE
            
            p_sub = tf_h.add_paragraph()
            p_sub.text = data["subtitle"]
            p_sub.font.name = 'Arial'
            p_sub.font.size = Pt(14)
            p_sub.font.color.rgb = COLOR_MUTED
            
            # 4 Metric Cards
            card_w = Inches(2.7)
            card_h = Inches(4.8)
            card_y = Inches(1.8)
            spacing = Inches(0.31)
            
            for m_idx, m_info in enumerate(data["metrics"]):
                card_x = Inches(0.8) + m_idx * (card_w + spacing)
                c_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, card_x, card_y, card_w, card_h)
                c_shape.fill.solid()
                c_shape.fill.fore_color.rgb = COLOR_CARD
                c_shape.line.color.rgb = COLOR_BORDER
                c_shape.line.width = Pt(1.2)
                
                tb = slide.shapes.add_textbox(card_x + Inches(0.2), card_y + Inches(0.4), card_w - Inches(0.4), card_h - Inches(0.8))
                tf_m = tb.text_frame
                tf_m.word_wrap = True
                
                p_hzn = tf_m.paragraphs[0]
                p_hzn.text = m_info["horizon"]
                p_hzn.alignment = PP_ALIGN.CENTER
                p_hzn.font.name = 'Arial'
                p_hzn.font.size = Pt(22)
                p_hzn.font.bold = True
                p_hzn.font.color.rgb = COLOR_WHITE
                
                p_r2 = tf_m.add_paragraph()
                p_r2.text = "\n" + m_info["r2"]
                p_r2.alignment = PP_ALIGN.CENTER
                p_r2.font.name = 'Arial'
                p_r2.font.size = Pt(20)
                p_r2.font.bold = True
                p_r2.font.color.rgb = COLOR_WHITE
                
                p_mae = tf_m.add_paragraph()
                p_mae.text = m_info["mae"]
                p_mae.alignment = PP_ALIGN.CENTER
                p_mae.font.name = 'Arial'
                p_mae.font.size = Pt(13.5)
                p_mae.font.color.rgb = COLOR_MUTED
                
                p_ds = tf_m.add_paragraph()
                p_ds.text = "\n" + m_info["desc"]
                p_ds.alignment = PP_ALIGN.CENTER
                p_ds.font.name = 'Arial'
                p_ds.font.size = Pt(12.5)
                p_ds.font.color.rgb = COLOR_LINE

    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "Roadlyy_Team_Culers_Presentation.pptx")
    prs.save(out_path)
    print(f"Presentation saved successfully to: {out_path}")

if __name__ == "__main__":
    create_presentation()
