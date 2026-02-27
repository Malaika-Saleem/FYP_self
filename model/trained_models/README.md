# DetectifAI Model

Accuracy: 99.35%
Classifier: svm
Classes: 30

## Files
- classifier_svm.pkl
- label_encoder.pkl
- metadata.json

## Integration

```python
import joblib

classifier = joblib.load('classifier_svm.pkl')
encoder = joblib.load('label_encoder.pkl')

# Use with DetectifAI
detectif = DetectifAI(
    ...,
    classifier_path='trained_models/classifier_svm.pkl',
    encoder_path='trained_models/label_encoder.pkl',
    enable_person_id=True
)
```
