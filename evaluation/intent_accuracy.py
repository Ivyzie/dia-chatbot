import json
import pandas as pd
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from intent_emotion_router import classify_intent
from dotenv import load_dotenv
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # 0=all, 1=info, 2=warning, 3=error
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'



def load_test_data(file_path):
    """Load test data from JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def evaluate_intent_classifier(test_data):
    """Evaluate intent classifier on test data"""
    results = []
    
    for item in test_data:
        query = item['query']
        true_intent = item['intent']
        
        # Get prediction from your classifier
        predicted_intent = classify_intent(query)
        
        results.append({
            'query': query,
            'true_intent': true_intent,
            'predicted_intent': predicted_intent,
            'correct': predicted_intent == true_intent
        })
    
    return pd.DataFrame(results)

def compute_metrics(results_df):
    """Compute classification metrics"""
    y_true = results_df['true_intent']
    y_pred = results_df['predicted_intent']
    
    # Overall accuracy
    accuracy = accuracy_score(y_true, y_pred)
    
    # Detailed classification report
    report = classification_report(y_true, y_pred, output_dict=True)
    
    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred, 
                          labels=sorted(results_df['true_intent'].unique()))
    
    return {
        'accuracy': accuracy,
        'report': report,
        'confusion_matrix': cm,
        'labels': sorted(results_df['true_intent'].unique())
    }

def plot_confusion_matrix(cm, labels, output_path=None):
    """Plot confusion matrix as heatmap"""
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=labels,
                yticklabels=labels)
    plt.xlabel('Predicted Intent')
    plt.ylabel('True Intent')
    plt.title('Confusion Matrix')
    
    if output_path:
        plt.savefig(output_path)
    else:
        plt.show()

def analyze_errors(results_df):
    """Analyze misclassified examples"""
    errors = results_df[results_df['correct'] == False].copy()
    return errors

def main():
    # Define output directory inside evaluation
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Load test data
    test_data = load_test_data('evaluation/intent_test_data.json')
    print(f"Loaded {len(test_data)} test examples")
    
    # Evaluate classifier
    results_df = evaluate_intent_classifier(test_data)
    
    # Compute metrics
    metrics = compute_metrics(results_df)
    
    # Print results
    print(f"\nOverall Accuracy: {metrics['accuracy']:.4f}")
    print("\nClassification Report:")
    report_df = pd.DataFrame(metrics['report']).transpose()
    print(report_df)
    
    # Plot confusion matrix
    plot_confusion_matrix(
        metrics['confusion_matrix'],
        metrics['labels'],
        str(output_dir / "confusion_matrix.png")
    )
    
    # Error analysis
    errors = analyze_errors(results_df)
    print(f"\nFound {len(errors)} misclassifications")
    
    # Save results
    results_df.to_csv(output_dir / "classification_results.csv", index=False)
    errors.to_csv(output_dir / "misclassifications.csv", index=False)
    
    print("\nResults saved to evaluation/output directory")

if __name__ == "__main__":
    main()