"""Where each tracked venue lives in the two community deadline datasets."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFERENCES_YML = REPO_ROOT / "_data" / "conferences.yml"

# Both lists are MIT-licensed and community-maintained. ccf-deadlines is the
# primary source (it is usually first to carry a new call); ai-deadlines from
# Hugging Face fills venues ccf-deadlines does not track.
CCF_RAW = "https://raw.githubusercontent.com/ccfddl/ccf-deadlines/main/"
HF_RAW = "https://raw.githubusercontent.com/huggingface/ai-deadlines/main/src/data/conferences/"

# Venue name in conferences.yml -> (ccf-deadlines path, ai-deadlines file stem).
# None: that list does not carry the venue. HRI, Humanoids and SIGGRAPH Asia
# are in neither, so they stay hand-maintained.
SOURCES = {
    # Robotics
    "ICRA": ("conference/AI/icra.yml", "icra"),
    "HRI": (None, None),
    "IROS": ("conference/AI/iros.yml", "iros"),
    "CoRL": ("conference/AI/corl.yml", "corl"),
    "RSS": ("conference/AI/rss.yml", "rss"),
    "Humanoids": (None, None),
    # Vision and graphics
    "IEEE VR": ("conference/CG/vr.yml", None),
    "CVPR": ("conference/AI/cvpr.yml", "cvpr"),
    "3DV": ("conference/CG/3dv.yml", "3dv"),
    "ICCV": ("conference/AI/iccv.yml", "iccv"),
    "MICCAI": ("conference/MX/miccai.yml", "miccai"),
    "SIGGRAPH": (None, "siggraph"),
    "SIGGRAPH Asia": (None, None),
    "ACM MM": ("conference/CG/mm.yml", "acm_mm"),
    "WACV": ("conference/AI/wacv.yml", "wacv"),
    "BMVC": ("conference/AI/bmvc.yml", None),
    "ECCV": ("conference/AI/eccv.yml", "eccv"),
    "ISMAR": ("conference/CG/ismar.yml", None),
    "ICDAR": ("conference/AI/icdar.yml", "icdar"),
    "ICME": ("conference/CG/icme.yml", None),
    "IEEE VIS": ("conference/CG/vis.yml", None),
    # AI and ML
    "ICLR": ("conference/AI/iclr.yml", "iclr"),
    "WWW": ("conference/MX/www.yml", "www"),
    "ICML": ("conference/AI/icml.yml", "icml"),
    "IJCAI": ("conference/AI/ijcai.yml", "ijcai"),
    "KDD": ("conference/DB/sigkdd.yml", "kdd"),
    "NeurIPS": ("conference/AI/nips.yml", "neurips"),
    "ACL": ("conference/AI/acl.yml", "acl"),
    "EMNLP": ("conference/AI/emnlp.yml", "emnlp"),
    "AAAI": ("conference/AI/aaai.yml", "aaai"),
    "UAI": ("conference/AI/uai.yml", "uai"),
    "Interspeech": ("conference/CG/interspeech.yml", "interspeech"),
    "ECIR": ("conference/DB/ecir.yml", "ecir"),
    "AAMAS": ("conference/AI/aamas.yml", "aamas"),
    "NAACL": ("conference/AI/naacl.yml", "naacl"),
    "COLT": ("conference/AI/colt.yml", "colt"),
    "ICAPS": ("conference/AI/icaps.yml", None),
    "ICDM": ("conference/DB/icdm.yml", "icdm"),
    "KR": ("conference/AI/kr.yml", None),
    "SIGIR": ("conference/DB/sigir.yml", "sigir"),
    "AISTATS": ("conference/AI/aistats.yml", "aistats"),
    "CIKM": ("conference/DB/cikm.yml", "cikm"),
    "EACL": ("conference/AI/eacl.yml", None),
    "ECAI": ("conference/AI/ecai.yml", "ecai"),
    "ECML-PKDD": ("conference/DB/pkdd.yml", "ecml_pkdd"),
    "GECCO": ("conference/AI/gecco.yml", None),
    "ISWC": ("conference/DB/iswc.yml", None),
    "PPSN": ("conference/AI/ppsn.yml", None),
    "RecSys": ("conference/DB/recsys.yml", None),
    "SDM": ("conference/DB/sdm.yml", None),
    "WSDM": ("conference/DB/wsdm.yml", "wsdm"),
    # HCI
    "CHI": ("conference/HI/chi.yml", "chi"),
    "PerCom": ("conference/HI/percom.yml", None),
    "UIST": ("conference/HI/uist.yml", None),
    "ASSETS": ("conference/HI/assets.yml", None),
    "CSCW": ("conference/HI/cscw.yml", None),
    "DIS": ("conference/HI/dis.yml", None),
    "HICSS": ("conference/HI/hicss.yml", "hicss"),
    "ICWSM": ("conference/HI/icwsm.yml", None),
    "IUI": ("conference/HI/iui.yml", "iui"),
}

# Venues that meet every other year: the edition after N is N + 2.
BIENNIAL = {"ICCV": 2, "ECCV": 2}

USER_AGENT = "s-elim.github.io deadline sync (+https://s-elim.github.io/deadlines/)"
