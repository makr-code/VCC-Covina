# 🤖 AI Judge Integration - Test Config

## LLM Konfiguration für Tests

Da die kommerziellen LLM APIs (OpenAI, Anthropic) nicht verfügbar sind, 
nutzen wir einen Mock-LLM für Tests.

### Verfügbare Optionen:

1. **Mock-LLM** (für Tests ohne API Keys)
   ```python
   judge_config = {
       'judge_models': ['mock:test-judge'],
       'evaluation_criteria': ['accuracy', 'completeness', 'relevance', 'compliance'],
       'german_legal_focus': True
   }
   ```

2. **OpenAI** (mit API Key)
   ```python
   judge_config = {
       'judge_models': ['openai:gpt-4o-mini'],
       'evaluation_criteria': ['accuracy', 'completeness', 'relevance', 'compliance'],
       'german_legal_focus': True
   }
   ```

3. **Anthropic** (mit API Key)
   ```python
   judge_config = {
       'judge_models': ['anthropic:claude-3-haiku'],
       'evaluation_criteria': ['accuracy', 'completeness', 'relevance', 'compliance'],
       'german_legal_focus': True
   }
   ```

4. **Multi-LLM Consensus**
   ```python
   judge_config = {
       'judge_models': [
           'openai:gpt-4o-mini',
           'anthropic:claude-3-haiku',
           'mock:test-judge'
       ],
       'evaluation_criteria': ['accuracy', 'completeness', 'relevance', 'compliance'],
       'consensus_threshold': 0.7,
       'german_legal_focus': True
   }
   ```

## API Keys Setup (Optional)

### OpenAI
```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."

# Linux/Mac
export OPENAI_API_KEY="sk-..."
```

### Anthropic
```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Linux/Mac
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Evaluation Kriterien

Die AI Judge bewertet nach folgenden Kriterien:

1. **Accuracy (30%)** - Faktische Korrektheit
2. **Completeness (25%)** - Vollständigkeit der Information
3. **Relevance (20%)** - Relevanz zum Kontext
4. **Clarity (10%)** - Klarheit der Formulierung
5. **Compliance (10%)** - Rechtliche Compliance (DSGVO, VwVfG, BauO)
6. **Consistency (5%)** - Konsistenz mit bestehendem Wissen

## Erwartete Ausgabe

```json
{
  "evaluation_score": 0.85,
  "confidence": 0.77,
  "gaps_evaluated": 5,
  "total_gaps": 5,
  "recommendations": [
    "Rechtszitate gemäß VwVfG § 39 vervollständigen",
    "DSGVO-konforme Formulierungen prüfen",
    "Prozessdokumentation in Abschnitt 3.2 erweitern"
  ]
}
```

## Test ohne LLM APIs

Die GUI fällt automatisch auf Mock zurück wenn keine APIs verfügbar sind:

```
⚠️ Commercial LLM APIs not available - using mock evaluation
🎭 Starte MOCK AI Evaluation (5 Gaps)
```

## Mock vs. Real Evaluation

### Mock (ohne APIs):
- Generiert zufällige Scores (0.7-0.95)
- Standard-Empfehlungen
- Sofortiges Ergebnis (2 Sekunden)

### Real (mit APIs):
- Echte LLM-basierte Bewertung
- Kontextspezifische Empfehlungen
- Langsamer (5-15 Sekunden pro Gap)
- Kosten pro API Call

## Nächste Schritte

Für produktive Nutzung:
1. OpenAI oder Anthropic API Keys besorgen
2. In Umgebungsvariablen setzen
3. `pip install openai anthropic`
4. GUI neu starten
