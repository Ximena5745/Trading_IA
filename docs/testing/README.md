# Testing Strategy

> Framework de testing, estrategias y estándares

---

## 1. TESTING PYRAMID

```
                    ┌─────────────┐
                    │     E2E     │  ← 5%
                   ┌─────────────┐
                  │  Integration │  ← 15%
                 ┌─────────────┐
                │    Unit      │  ← 80%
               └──────────────┘
```

### 1.1 Distribución

| Nivel | Porcentaje | Responsabilidad |
|-------|------------|-----------------|
| Unit | 80% | Developers |
| Integration | 15% | Developers + QA |
| E2E | 5% | QA + Automated |

---

## 2. UNIT TESTS

### 2.1 Estructura

```
tests/
├── unit/
│   ├── domain/
│   │   ├── test_signal.py
│   │   ├── test_order.py
│   │   └── test_portfolio.py
│   ├── core/
│   │   ├── risk/
│   │   │   ├── test_risk_manager.py
│   │   │   └── test_kill_switch.py
│   │   ├── signals/
│   │   │   └── test_signal_engine.py
│   │   └── ...
│   └── api/
│       └── test_dependencies.py
```

### 2.2 Conventions

```python
import pytest
from domain.entities import Signal

class TestSignal:
    def test_buy_signal_invariants(self):
        signal = Signal(
            id="sig_123",
            symbol="BTCUSDT",
            action="BUY",
            entry_price=45000.0,
            stop_loss=44000.0,
            take_profit=47000.0,
            confidence=0.8
        )
        assert signal.is_valid_for_buy()
    
    def test_confidence_range(self):
        with pytest.raises(ValueError):
            Signal(
                # ...
                confidence=1.5  # Invalid
            )
    
    @pytest.mark.parametrize("action,expected", [
        ("BUY", "BUY"),
        ("SELL", "SELL"),
        ("HOLD", "HOLD"),
    ])
    def test_valid_actions(self, action, expected):
        # Test parametrizado
```

### 2.3 Coverage Target

```python
# pyproject.toml
[tool.coverage.run]
source = ["api", "core"]
omit = ["tests/*", "scripts/*"]

[tool.coverage.report]
precision = 2
show_missing = true
```

| Module | Target |
|--------|--------|
| Domain entities | 95% |
| Risk engine | 90% |
| Signal engine | 85% |
| Execution | 80% |
| API | 80% |

---

## 3. INTEGRATION TESTS

### 3.1 Estructura

```
tests/
└── integration/
    ├── test_pipeline_paper.py
    ├── test_api_execution.py
    └── test_database.py
```

### 3.2 Ejemplo

```python
import pytest
from httpx import AsyncClient
from api.main import app

@pytest.mark.integration
class TestExecutionAPI:
    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as c:
            yield c
    
    async def test_execute_order_paper(self, client, auth_token):
        response = await client.post(
            "/execution/order",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "signal_id": "sig_123",
                "quantity": 0.1,
                "execution_mode": "paper"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "filled"
```

### 3.3 Test Database

```python
# tests/conftest.py
@pytest.fixture
async def db_session():
    # Use test database
    engine = create_engine("postgresql://test:test@localhost/test_db")
    async with engine.begin() as session:
        yield session
        await session.rollback()
```

---

## 4. E2E TESTS

### 4.1 Estructura

```
tests/
└── e2e/
    └── test_dashboard_e2e.py
```

### 4.2 Ejemplo

```python
import pytest
from playwright.sync_api import Page

@pytest.mark.e2e
class TestDashboard:
    def test_login_and_view_portfolio(self, page: Page):
        # Navigate
        page.goto("http://localhost:8501")
        
        # Login
        page.fill("[data-testid='username']", "admin")
        page.fill("[data-testid='password']", "password")
        page.click("[data-testid='login-btn']")
        
        # Verify portfolio
        assert page.locator("[data-testid='portfolio-value']").is_visible()
```

---

## 5. QUANT TESTS

### 5.1 Backtesting Tests

```python
# tests/quant/test_strategy.py
import pytest
from core.strategies import EmaRsiStrategy
from core.backtesting import BacktestEngine

@pytest.mark.quant
class TestStrategy:
    def test_ema_rsi_walk_forward(self):
        engine = BacktestEngine(
            strategy=EmaRsiStrategy(fast_ema=9, slow_ema=21),
            initial_capital=10000
        )
        
        # Walk-forward
        results = engine.run_walk_forward(
            data=historical_data,
            train_window="2y",
            test_window="3m"
        )
        
        # Assertions
        assert results.sharpe_ratio > 0.5
        assert results.max_drawdown < 0.20
        assert results.win_rate > 0.40
```

### 5.2 Stress Testing

```python
@pytest.mark.quant
class TestStress:
    def test_high_volatility(self):
        # Simular condiciones extremas
        stressed_data = apply_volatility_multiplier(data, 3.0)
        
        result = strategy.run(stressed_data)
        assert result.sharpe_ratio > 0  # Still profitable
```

---

## 6. TEST INFRASTRUCTURE

### 6.1 Pytest Config

```ini
# pytest.ini
[pytest]
minversion = 8.0
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -ra
    --strict-markers
    --tb=short
    -v
markers =
    slow: marks tests as slow
    integration: integration tests
    unit: unit tests
    e2e: end-to-end tests
    quant: quantitative tests
```

### 6.2 Fixtures

```python
# tests/conftest.py
import pytest
from core.db import get_test_session

@pytest.fixture
async def session():
    async with get_test_session() as session:
        yield session

@pytest.fixture
def sample_signal():
    return Signal(
        id="sig_test",
        symbol="BTCUSDT",
        action="BUY",
        entry_price=45000.0,
        stop_loss=44000.0,
        take_profit=47000.0,
        confidence=0.8
    )

@pytest.fixture
async def auth_token():
    # Generate test token
    return create_test_token(role="admin")
```

---

## 7. CI/CD INTEGRATION

### 7.1 Quality Gates

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      
      - name: Run linters
        run: |
          ruff check api/ core/
          black --check api/ core/
          mypy api/ core/
      
      - name: Run tests
        run: |
          pytest tests/unit --cov=core --cov=api --cov-report=xml
          pytest tests/integration
          pytest tests/quant
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### 7.2 Gates

| Gate | Tool | Threshold |
|------|------|-----------|
| Lint | Ruff | 0 errors |
| Format | Black | 0 changes |
| Type Check | MyPy | 0 errors |
| Security | Bandit | 0 highs |
| Unit Coverage | Coverage | > 80% |
| Tests | pytest | 100% pass |

---

## 8. BEST PRACTICES

### 8.1 Naming

| Pattern | Example |
|---------|---------|
| Test file | `test_signal.py` |
| Test class | `TestSignal` |
| Test function | `test_buy_signal_valid` |
| Fixtures | `sample_signal`, `db_session` |

### 8.2 AAA Pattern

```python
def test_example(self):
    # Arrange
    signal = Signal(...)
    
    # Act
    result = validate_signal(signal)
    
    # Assert
    assert result.approved
```

### 8.3 No Magic Numbers

```python
# BAD
assert confidence > 0.7

# GOOD
MIN_CONFIDENCE = 0.7
assert confidence > MIN_CONFIDENCE
```

---

## 9. MOCKING

### 9.1 External Services

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_execution_with_mocked_exchange():
    with patch("core.execution.binance_client.BinanceClient") as mock:
        mock.execute_order = AsyncMock(
            return_value=ExecutionResult(
                order_id="mock_123",
                status=OrderStatus.FILLED
            )
        )
        
        result = await executor.execute(signal, 0.1)
        assert result.status == OrderStatus.FILLED
```

---

## 10. TESTING STRATEGY BY COMPONENT

| Component | Test Types | Focus |
|-----------|------------|-------|
| Domain Entities | Unit | Invariants, validation |
| Risk Engine | Unit + Integration | All scenarios, edge cases |
| Signal Engine | Unit + Quant | Accuracy, SHAP |
| Execution | Unit + Integration | Error handling |
| ML Models | Quant | Walk-forward, stress |
| API | Integration + E2E | Happy path, errors |

---

## 11. METRICS

| Métrica | Target |
|---------|--------|
| Coverage (unit) | > 80% |
| Coverage (total) | > 70% |
| Test execution time | < 10 min |
| Flaky tests | < 1% |

---

*Volver al [INDEX](INDEX.md)*