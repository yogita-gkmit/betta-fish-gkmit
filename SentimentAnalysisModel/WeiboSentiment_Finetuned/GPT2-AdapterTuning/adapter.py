import torch
import torch.nn as nn

class AdapterLayer(nn.Module):
    """
    Adapter Layer Implementation
    Adding it to Transformer layers allows parameter-efficient fine-tuning
    """
    def __init__(self, input_size, adapter_size):
        super(AdapterLayer, self).__init__()
        # Dimension reduction FC layer
        self.down_project = nn.Linear(input_size, adapter_size)
        # Activation function
        self.activation = nn.ReLU()
        # Dimension elevation FC layer
        self.up_project = nn.Linear(adapter_size, input_size)
        
        # Initialize parameters
        self._init_weights()
    
    def _init_weights(self):
        # Initialize down_project with small values
        nn.init.normal_(self.down_project.weight, std=1e-2)
        nn.init.zeros_(self.down_project.bias)
        
        # Initialize up_project with values close to zero, ensuring small impact on original model in early training
        nn.init.normal_(self.up_project.weight, std=1e-2)
        nn.init.zeros_(self.up_project.bias)
    
    def forward(self, x):
        # Save original input for residual connection
        residual = x
        
        # Pass through reduction layer
        x = self.down_project(x)
        # Activation
        x = self.activation(x)
        # Pass through elevation layer
        x = self.up_project(x)
        
        # Residual connection
        return residual + x 