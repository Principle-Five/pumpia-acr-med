import sys
from pathlib import Path

from pumpia.module_handling.module_collections import BaseCollection
from pumpia.module_handling.in_outs.viewer_ios import MonochromeDicomViewerIO

if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from pumpia_acr_med.med_acr_context import MedACRContextManagerGenerator


class ContextTest(BaseCollection):
    context_manager_generator = MedACRContextManagerGenerator()

    main = MonochromeDicomViewerIO(0, 0)


if __name__ == "__main__":
    ContextTest.run()
