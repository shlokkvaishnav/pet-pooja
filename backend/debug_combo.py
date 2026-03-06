"""Debug why the correlation pipeline fails on the live server."""
import sys
import os
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(name)s: %(message)s')

from database import SessionLocal
from modules.revenue.combo_engine import _run_ml_pipeline, _COMBO_MIN_CORRELATION, _COMBO_MAX_COMBOS, _COMBO_WINDOW_SIZE, _COMBO_DEFAULT_DISCOUNT_PCT

db = SessionLocal()
try:
    _run_ml_pipeline(
        db,
        min_support=_COMBO_MIN_CORRELATION,
        min_confidence=0.0,
        min_lift=0.0,
        max_combos=_COMBO_MAX_COMBOS,
        window_size=_COMBO_WINDOW_SIZE,
        target_discount_pct=_COMBO_DEFAULT_DISCOUNT_PCT,
    )
    print("Pipeline completed OK")
except Exception as e:
    import traceback
    print("PIPELINE ERROR:")
    print(traceback.format_exc())
finally:
    db.close()
