# Remote Sensing Methodology — Satellite Intelligence Explorer

## 1. Spectral Index Formulas

All spectral indices are computed using normalised difference ratios:

$$\text{Index} = \frac{\rho_A - \rho_B}{\rho_A + \rho_B}$$

Band designations correspond to Sentinel-2 Multi-Spectral Instrument (MSI):

| Indicator | Formal Name | Formula | Sentinel-2 Bands | Central Wavelengths | Primary Biophysical Significance | Reference |
|---|---|---|---|---|---|---|
| **NDVI** | Normalised Difference Vegetation Index | $\frac{\text{NIR} - \text{Red}}{\text{NIR} + \text{Red}}$ | $\frac{B8 - B4}{B8 + B4}$ | 842 nm / 665 nm | Canopy chlorophyll absorption and photosynthetic vigour | Rouse et al. (1974) |
| **NDMI** | Normalised Difference Moisture Index | $\frac{\text{NIR} - \text{SWIR}_1}{\text{NIR} + \text{SWIR}_1}$ | $\frac{B8 - B11}{B8 + B11}$ | 842 nm / 1610 nm | Canopy liquid water content and foliar moisture stress | Gao (1996) |
| **NDWI** | Normalised Difference Water Index | $\frac{\text{Green} - \text{NIR}}{\text{Green} + \text{NIR}}$ | $\frac{B3 - B8}{B3 + B8}$ | 560 nm / 842 nm | Delineation of open water bodies and surface inundation | McFeeters (1996) |
| **NDBI** | Normalised Difference Built-up Index | $\frac{\text{SWIR}_1 - \text{NIR}}{\text{SWIR}_1 + \text{NIR}}$ | $\frac{B11 - B8}{B11 + B8}$ | 1610 nm / 842 nm | Impervious surfaces, urban fabric, and compacted bare soil | Zha et al. (2003) |

---

## 2. Multi-Temporal Change Detection

Multi-temporal change compares two distinct observation epochs ($T_1$ and $T_2$):

1. **Absolute Change:**
   $$\Delta \text{Index} = \text{Index}_{T2} - \text{Index}_{T1}$$
2. **Relative Change (%):**
   $$\% \Delta = \frac{\text{Index}_{T2} - \text{Index}_{T1}}{|\text{Index}_{T1}|} \times 100$$
   *(Evaluated only where $|\text{Index}_{T1}| > 0.01$ to prevent asymptote distortions)*
3. **Spatial Classification:**
   $$\text{Class} = \begin{cases} \text{Increase (Gain)}, & \Delta \text{Index} > +0.05 \\ \text{Decrease (Reduction)}, & \Delta \text{Index} < -0.05 \\ \text{Stable}, & |\Delta \text{Index}| \le 0.05 \end{cases}$$

---

## 3. Statistical Anomaly Detection

Vegetation anomalies are identified via standard deviation z-score departures from a multi-season historical baseline:

$$z = \frac{\mu_{\text{current}} - \mu_{\text{baseline}}}{\sigma_{\text{baseline}}}$$

Where:
- $\mu_{\text{baseline}}$ is the pixel-level spatial mean across historical observations.
- $\sigma_{\text{baseline}}$ is the historical standard deviation (clamped to $\ge 0.01$ to avoid division by zero).

### Anomaly Classification Thresholds:
- **NORMAL:** $|z| < 1.0\sigma$ (Within normal historical variance)
- **WATCH:** $1.0\sigma \le |z| < 1.5\sigma$ (Mild departure from seasonal expectation)
- **WARNING:** $1.5\sigma \le |z| < 2.0\sigma$ (Moderate anomaly; environmental stress indicated)
- **ALERT:** $|z| \ge 2.0\sigma$ (Severe statistical outlier requiring ground verification)

> [!IMPORTANT]
> **Ethical & Scientific Caveat:**
> An Earth Observation anomaly is an optical indicator, not definitive ground truth. Cloud shadow, phenological shifts, or tillage can trigger statistical anomalies. The platform deliberately labels these as "Potential Anomaly Detected" and never asserts ground truth crop failure without field verification.

---

## 4. Rule-Based Land Cover Classification

A deterministic hierarchical decision tree classifies the landscape into 5 broad functional categories:

1. **Water:** $\text{NDWI} > 0.20$
2. **Built-up:** $\neg \text{Water} \wedge (\text{NDBI} > 0.10) \wedge (\text{NDVI} < 0.20)$
3. **Bare land:** $\neg \text{Water} \wedge \neg \text{Built-up} \wedge (\text{NDVI} < 0.15) \wedge (\text{NDBI} \le 0.10)$
4. **Vegetation:** $\neg \text{Water} \wedge \neg \text{Built-up} \wedge \neg \text{Bare land} \wedge (\text{NDVI} \ge 0.45)$
5. **Cropland:** All remaining valid non-water pixels ($0.15 \le \text{NDVI} < 0.45$)

---

## 5. Demonstration Data Disclosure

> **DEMONSTRATION DATA**
>
> This project uses deterministic synthetic reflectance data to demonstrate the Earth-observation processing pipeline. The remote-sensing calculations are real, but the demonstration raster values are not measurements from current satellite acquisitions.
