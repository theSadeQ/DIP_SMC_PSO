.. code-block:: bash

   # Basic simulation with classical controller
   python simulate.py --ctrl classical_smc --plot
   
   # Optimize and save controller gains
   python simulate.py --ctrl sta_smc --run-pso --save tuned_gains.json
   
   # Launch web interface
   streamlit run streamlit_app.py
