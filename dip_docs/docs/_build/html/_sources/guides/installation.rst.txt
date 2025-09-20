Installation
============

Requirements
------------
- Python 3.9+ recommended
- pip
- (Optional) virtualenv/conda for isolated environments

Steps
-----
1. Clone the repository
.. code-block:: bash

   git clone https://github.com/theSadeQ/DIP_SMC_PSO.git
   cd DIP_SMC_PSO


2. (Optional) Create & activate a virtual environment
.. code-block:: bash

   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate


3. Install dependencies
.. code-block:: bash

   pip install -r requirements.txt


4. Verify installation
.. code-block:: bash

   python -c "import numpy, scipy; print('OK')"
