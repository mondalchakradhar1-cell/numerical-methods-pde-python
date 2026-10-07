import json, sys
from reference import SHEETS
r = json.load(open(sys.argv[1]))
for x in r:
    s = SHEETS.get(x['layout'], {}).get(x['m_gs'])
    ref = f"| sheet {s[0]:6.1f} {s[1]:.3f} {s[2]:6.2f} {s[3]:5.1f} {s[4]}-{s[5]}" if s else ""
    print(f"{x['layout']:8s} {x['m_gs']:5.1f} spread {x['spread_mK']:6.1f} inlet {x['inlet_C']:.3f} dp {x['dp_kPa']:6.2f} UA {x['UA_WK']:5.1f} "
          f"Re {x['Re'][0]:.0f}-{x['Re'][1]:.0f} bal {x['energy_balance_W']:.0e} it {x['solve']['iters']} {x['seconds']:.0f}s {ref}")
