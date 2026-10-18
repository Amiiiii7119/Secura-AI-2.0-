# Training Configuration and Hyperparameter Recipes

## 1. Linear Probe Training Recipe
* **Backbone:** OpenAI CLIP ViT-L/14 (Frozen, `requires_grad=False`)
* **Feature Dimension:** 768
* **Classifier:** Linear layer $768 \to 2$ with optional MLP projection ($768 \to 256 \to 2$, GELU activation, Dropout 0.1)
* **Loss Function:** Binary Cross-Entropy with Logits (`torch.nn.BCEWithLogitsLoss`)
* **Optimizer:** AdamW (Learning rate: $1\times 10^{-4}$, Weight decay: 0.01, Betas: (0.9, 0.999))
* **Batch Size:** 64
* **Epochs:** 10 with Early Stopping (Patience = 3 on validation AUROC)
* **Data Augmentations:**
  - RandomResizedCrop(224, scale=(0.8, 1.0))
  - RandomHorizontalFlip(p=0.5)
  - ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1)
  - JPEGCompression(quality_range=(50, 95), p=0.5)
  - GaussianBlur(kernel_size=3, sigma=(0.1, 1.0), p=0.2)\n