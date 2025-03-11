import sys
from pathlib import Path


if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from pumpia_acr_med.med_acr_collection import MedACRrptCollection

MedACRrptCollection.run()
