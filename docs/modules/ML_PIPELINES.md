# Módulo: ML Pipelines

> Pipelines de entrenamiento, inferencia y monitoreo de ML

---

## 1. OBJETIVO

Proveer pipelines robustos para entrenamiento de modelos, inferencia en producción, monitoreo de drift, validación y MLOps.

---

## 2. RESPONSABILIDADES

| Responsabilidad | Descripción |
|----------------|-------------|
| Model training | Entrenamiento de modelos |
| Model inference | Predicciones en producción |
| Drift detection | Detección de data/concept drift |
| Model validation | Validación de modelos |
| Online learning | Actualización incremental |

---

## 3. ARQUITECTURA INTERNA

```
┌─────────────────────────────────────────────────────────────────┐
│                       ML PIPELINES                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Training   │  │  Inference   │  │   Monitoring │        │
│  │   Pipeline   │  │   Pipeline   │  │   Pipeline   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│         │                │                │                    │
│         ▼                ▼                ▼                    │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                     ML Infrastructure                      │ │
│  │  - Model storage                                           │ │
│  │  - Feature store                                           │ │
│  │  - Experiment tracking                                      │ │
│  │  - Model registry                                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. COMPONENTES

### 4.1 Training Pipeline

**Archivos:** `scripts/train_*.py`, `scripts/run_training_pipeline.py`

**Pipeline:**
```python
class TrainingPipeline:
    async def run(
        self,
        asset: str,
        timeframe: str,
        model_type: str
    ) -> TrainingResult:
        
        # 1. Fetch data
        data = await self._fetch_data(asset, timeframe)
        
        # 2. Feature engineering
        features = self._feature_engineering(data)
        
        # 3. Split (walk-forward)
        train, val, test = self._split_walk_forward(features)
        
        # 4. Train model
        model = self._train(train, model_type)
        
        # 5. Validate
        metrics = self._validate(model, val)
        
        # 6. Save model
        await self._save_model(model, metrics)
        
        return TrainingResult(model, metrics)
```

**Parámetros de entrenamiento:**
| Parámetro | Valor |
|-----------|-------|
| Model | LightGBM |
| Objective | multiclass |
| Classes | BUY, SELL, HOLD |
| Max depth | 6 |
| Learning rate | 0.05 |
| Early stopping | 50 rounds |

### 4.2 Inference Pipeline

**Archivos:** `core/models/`, `core/ml/`

```python
class InferencePipeline:
    async def predict(
        self,
        model_name: str,
        features: pd.DataFrame
    ) -> PredictionResult:
        
        # 1. Load model
        model = await self._load_model(model_name)
        
        # 2. Predict
        prediction = model.predict(features)
        proba = model.predict_proba(features)
        
        # 3. SHAP explain
        explanation = self._explain(model, features)
        
        return PredictionResult(prediction, proba, explanation)
```

### 4.3 DriftDetector

**Archivo:** `core/ml/drift_detector.py`

**Tipos de drift:**
| Tipo | Descripción | Detección |
|------|-------------|-----------|
| Data drift | Cambios en features | KS test, PSI |
| Concept drift | Cambios en relación | Accuracy drop |
| Prediction drift | Cambios en predictions | Distribution shift |

```python
class DriftDetector:
    def detect_data_drift(
        self,
        current: pd.DataFrame,
        reference: pd.DataFrame,
        threshold: float = 0.1
    ) -> DriftReport:
        # Population Stability Index
        psi = self._calculate_psi(current, reference)
        
        return DriftReport(
            has_drift=psi > threshold,
            psi_value=psi,
            drifted_features=[...]
        )
    
    def detect_concept_drift(
        self,
        predictions: list,
        actuals: list,
        window_size: int = 100
    ) -> DriftReport:
        # Compare accuracy windows
        recent_acc = accuracy(recent_preds, recent_actuals)
        baseline_acc = accuracy(baseline_preds, baseline_actuals)
        
        if recent_acc < baseline_acc * 0.9:
            return DriftReport(has_drift=True, ...)
```

### 4.4 ModelValidationGate

**Archivo:** `core/ml/model_validation_gate.py`

**Validaciones pre-deploy:**
```python
class ModelValidationGate:
    async def validate(
        self,
        model_path: str,
        validation_data: pd.DataFrame
    ) -> ValidationResult:
        
        checks = [
            self._check_accuracy(min=0.50),
            self._check_fairness(),
            self._check_stability(),
            self._check_drift(),
        ]
        
        return ValidationResult(passed=all(checks), details=checks)
```

### 4.5 StressTesting

**Archivo:** `core/ml/stress_testing.py`

**Escenarios:**
| Escenario | Descripción |
|-----------|-------------|
| High volatility | Multiplicar volatilidad |
| Low liquidity | Simular slippage |
| Market crash | Caída 30% en horas |
| Regime change | Cambiar régimen |

### 4.6 AlphaDecayMonitor

**Archivo:** `core/ml/alpha_decay_monitor.py`

**Propósito:** Monitorear degradación de performance.

```python
class AlphaDecayMonitor:
    def check_alpha_decay(
        self,
        recent_performance: PerformanceMetrics,
        baseline_performance: PerformanceMetrics
    ) -> DecayReport:
        # Alert si performance baja > 20% vs baseline
        decay_pct = (baseline - recent) / baseline
        
        return DecayReport(
            has_decay=decay_pct > 0.2,
            decay_pct=decay_pct,
            recommendation="retrain" if decay_pct > 0.3 else "monitor"
        )
```

### 4.7 OnlineLearningAgent

**Archivo:** `core/ml/online_learning_agent.py`

**Propósito:** Actualización incremental de modelos.

```python
class OnlineLearningAgent:
    async def update(
        self,
        new_data: pd.DataFrame,
        triggers: list[str]
    ) -> UpdateResult:
        # Solo actualizar si drift detectado o threshold
        if "drift" in triggers or "scheduled" in triggers:
            model.update(new_data)
            model.save()
```

---

## 5. MODEL STORAGE

### 5.1 Estructura

```
data/models/
├── technical/
│   ├── v1.0/
│   │   ├── model.pkl
│   │   ├── config.yaml
│   │   └── metrics.json
│   └── v1.1/
├── regime/
│   └── ...
└── meta/
    └── ...
```

### 5.2 Registry

```python
class ModelRegistry:
    async def register(
        self,
        name: str,
        version: str,
        model_path: str,
        metrics: dict
    ) -> None: ...
    
    async def get_latest(self, name: str) -> ModelInfo: ...
    
    async def list_models(self) -> list[ModelInfo]: ...
```

---

## 6. EVENTOS

### 6.1 Eventos Publicados

| Evento | Descripción | Payload |
|--------|-------------|---------|
| `ml.model_trained` | Modelo entrenado | `{model, metrics}` |
| `ml.model_deployed` | Modelo deployed | `{model, version}` |
| `ml.drift_detected` | Drift detectado | `{drift_type, details}` |
| `ml.alpha_decay` | Alpha decay | `{decay_pct}` |

### 6.2 Eventos Consumidos

| Evento | Descripción |
|--------|-------------|
| (manual trigger) | Entrenamiento |

---

## 7. OBSERVABILIDAD

### 7.1 Métricas

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `ml.training.time` | Histogram | Tiempo entrenamiento |
| `ml.inference.latency` | Histogram | Latencia inferencia |
| `ml.drift.psi` | Gauge | PSI value |
| `ml.model_accuracy` | Gauge | Accuracy actual |
| `ml.predictions.count` | Counter | Predicciones |

### 7.2 Logs

```json
{
  "event": "model_trained",
  "model": "technical_btcusdt",
  "version": "1.2",
  "accuracy": 0.58,
  "precision": 0.55,
  "recall": 0.52,
  "training_time_min": 45
}
```

```json
{
  "event": "drift_detected",
  "type": "data_drift",
  "psi": 0.15,
  "drifted_features": ["volume", "volatility"],
  "recommendation": "retrain"
}
```

---

## 8. TESTING REQUERIDO

| Test | Tipo | Cobertura objetivo |
|------|------|---------------------|
| test_training | Unit | 80% |
| test_inference | Unit | 90% |
| test_drift_detection | Unit | 90% |
| test_validation_gate | Unit | 90% |

---

## 9. EJEMPLOS DE USO

```python
# Entrenar modelo
pipeline = TrainingPipeline()
result = await pipeline.run(
    asset="BTCUSDT",
    timeframe="1h",
    model_type="lightgbm"
)

# Inferencia
inference = InferencePipeline()
pred = await inference.predict("technical_v1", features)

# Monitorear drift
drift_detector = DriftDetector()
report = drift_detector.detect_data_drift(current, reference)
if report.has_drift:
    alert("Data drift detected, consider retraining")
```

---

## 10. KPIs

| KPI | Target |
|-----|--------|
| Model accuracy | > 50% (baseline) |
| Drift detection latency | < 5min |
| Training success rate | > 95% |
| Inference latency | < 100ms |

---

*Volver al [INDEX](../INDEX.md)*