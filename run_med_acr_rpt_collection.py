# command line "python -m nuitka .\run_med_acr_rpt_collection.py"

# nuitka-project-if: {OS} in ("Windows", "Linux", "Darwin", "FreeBSD"):
#    nuitka-project: --onefile
# nuitka-project-else:
#    nuitka-project: --mode=onefile

# nuitka-project: --enable-plugin=tk-inter

# PyDICOM decoders must be manually included
# nuitka-project: --include-module=pydicom.pixels.decoders.base
# nuitka-project: --include-module=pydicom.pixels.decoders.gdcm
# nuitka-project: --include-module=pydicom.pixels.decoders.pillow
# nuitka-project: --include-module=pydicom.pixels.decoders.pyjpegls
# nuitka-project: --include-module=pydicom.pixels.decoders.pylibjpeg
# nuitka-project: --include-module=pydicom.pixels.decoders.rle
# nuitka-project: --include-module=pydicom.pixels.encoders.base
# nuitka-project: --include-module=pydicom.pixels.encoders.gdcm
# nuitka-project: --include-module=pydicom.pixels.encoders.native
# nuitka-project: --include-module=pydicom.pixels.encoders.pyjpegls
# nuitka-project: --include-module=pydicom.pixels.encoders.pylibjpeg
# nuitka-project: --include-package-data=pydicom

from pumpia_acr_med.med_acr_rpt_collection import MedACRrptCollection

MedACRrptCollection.run()
