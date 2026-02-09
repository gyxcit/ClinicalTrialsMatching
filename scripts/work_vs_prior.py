import pandas as pd
import matplotlib.pyplot as plt

# Créer le DataFrame pour la table
data = {
    "Approach": [
        "Rule-based systems",
        "NLP / ML matching (traditional)",
        "Embedding / similarity methods",
        "LLM-based matching",
        "Bayesian/probabilistic scoring",
        "This work (graded scoring)"
    ],
    "Binary eligibility logic": [
        "Yes", "Yes / Partial", "Partial", "Partial", "No / Partial", "No"
    ],
    "Uncertainty explicitly modeled": [
        "No", "No", "No", "No / Partial", "Yes", "Yes"
    ],
    "Ordinal/Monotonic evaluation of scores": [
        "No", "No", "No", "No", "Partial", "Yes"
    ],
    "Calibration analysis": [
        "No", "No", "No", "No", "Partial", "Yes"
    ],
    "Patient-reported uncertainty": [
        "No", "No", "No", "Partial / No", "No / Partial", "Yes"
    ]
}

df = pd.DataFrame(data)

# Dessiner la figure
fig, ax = plt.subplots(figsize=(11, 3))
ax.axis('tight')
ax.axis('off')

# Créer le tableau
table = ax.table(
    cellText=df.values,
    colLabels=df.columns,
    cellLoc='center',
    loc='center'
)

table.auto_set_font_size(False)
table.set_fontsize(8)
table.scale(1.2, 1)

plt.tight_layout()
plt.savefig("table1_positioning.png", dpi=300, bbox_inches='tight')
plt.show()
