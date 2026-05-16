import sys
from pathlib import Path

from pumpia.module_handling.collections import BaseCollection
from pumpia.module_handling.fields.viewer_fields import MonochromeDicomViewerField

if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from pumpia_acr_med.med_acr_context import MedACRContextManager


class ContextTest(BaseCollection):
    context_manager = MedACRContextManager()

    main = MonochromeDicomViewerField(0, 0)


if __name__ == "__main__":
    ContextTest.run()
