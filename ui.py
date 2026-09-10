NAVY = "#163A63"
LINE = "#E2E8F0"
BLUE = "#2563EB"
GREY = "#94A3B8"
TEAL = "#0F766E"
CHART = dict(displayModeBar=False)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
h1.main-title { color: #163A63 !important; font-weight: 700 !important; font-size: 28px !important; margin-bottom: 2px !important; }
.header-block { margin-bottom: 12px; padding-bottom: 12px; border-bottom: 2px solid #E2E8F0; }
.header-block .tagline { color: #64748B; font-size: 13px; margin: 0; }
div[data-testid="stMetric"] { background: #fff !important; border: 1px solid #E2E8F0 !important; border-radius: 10px !important; padding: 16px 20px !important; box-shadow: 0 1px 3px rgba(15,23,42,.06) !important; }
div[data-testid="stMetricLabel"] p { font-size: 12px !important; color: #64748B !important; font-weight: 500 !important; }
div[data-testid="stMetricValue"] { font-size: 22px !important; font-weight: 700 !important; color: #172033 !important; }
.stMainBlockContainer { padding-top: 1rem !important; }
</style>
"""


def header(title, tagline):
    return f"""
<div class=\"header-block\">
  <h1 class=\"main-title\">{title}</h1>
  <p class=\"tagline\">{tagline}</p>
</div>
"""
