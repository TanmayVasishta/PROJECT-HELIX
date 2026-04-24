import sys
sys.path.insert(0, r"C:\Users\tanma\HELIX")
from core.oracle.cloud import CloudOracle
o = CloudOracle()
print(o.status())
