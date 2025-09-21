# System Diagrams

This section provides comprehensive visual representations of the double-inverted pendulum system, including physical structure, coordinate systems, and signal flow diagrams.

## Physical System Architecture

### Double-Inverted Pendulum Structure

```{mermaid}
flowchart TB
    subgraph "Physical Plant"
        direction TB
        Cart[Cart<br/>Mass: m₀ = 1.0 kg<br/>Position: x(t)]

        subgraph "Pendulum Assembly"
            Pend1[Pendulum 1<br/>Mass: m₁ = 0.1 kg<br/>Length: l₁ = 0.5 m<br/>Angle: θ₁(t)]
            Pend2[Pendulum 2<br/>Mass: m₂ = 0.1 kg<br/>Length: l₂ = 0.5 m<br/>Angle: θ₂(t)]
        end

        Cart --> Pend1
        Pend1 --> Pend2
    end

    subgraph "Actuation System"
        Motor[DC Motor<br/>Force: u(t)<br/>Range: ±50 N]
        Amplifier[Power Amplifier<br/>Voltage: ±10 V]
        Controller[Digital Controller<br/>Sample Rate: 1 kHz]
    end

    subgraph "Sensing System"
        PosSensor[Position Encoder<br/>Resolution: 0.1 mm<br/>Measurement: x(t)]
        AngleSensor1[Angle Encoder 1<br/>Resolution: 0.01°<br/>Measurement: θ₁(t)]
        AngleSensor2[Angle Encoder 2<br/>Resolution: 0.01°<br/>Measurement: θ₂(t)]
    end

    Controller --> Amplifier
    Amplifier --> Motor
    Motor -->|Force u(t)| Cart

    Cart --> PosSensor
    Pend1 --> AngleSensor1
    Pend2 --> AngleSensor2

    PosSensor --> Controller
    AngleSensor1 --> Controller
    AngleSensor2 --> Controller

    style Cart fill:#e1f5fe
    style Pend1 fill:#f3e5f5
    style Pend2 fill:#f3e5f5
    style Controller fill:#e8f5e8
```

### Coordinate System Definition

```{mermaid}
flowchart LR
    subgraph "Coordinate Frame"
        Origin[Origin<br/>Fixed Point<br/>x = 0]
        XAxis[X-Axis<br/>Horizontal<br/>Positive → Right]
        YAxis[Y-Axis<br/>Vertical<br/>Positive ↑ Up]
    end

    subgraph "Generalized Coordinates"
        CartPos[Cart Position<br/>x(t) ∈ ℝ<br/>Range: ±2 m]
        Angle1[Pendulum 1 Angle<br/>θ₁(t) ∈ ℝ<br/>Upward = 0]
        Angle2[Pendulum 2 Angle<br/>θ₂(t) ∈ ℝ<br/>Upward = 0]
    end

    subgraph "State Vector"
        StateVec[q⃗(t) = [x, θ₁, θ₂]ᵀ<br/>x⃗(t) = [q⃗ᵀ, q⃗̇ᵀ]ᵀ ∈ ℝ⁶]
    end

    Origin --> CartPos
    XAxis --> CartPos
    YAxis --> Angle1
    YAxis --> Angle2

    CartPos --> StateVec
    Angle1 --> StateVec
    Angle2 --> StateVec

    style Origin fill:#fff3e0
    style StateVec fill:#e8f5e8
```

## Control System Architecture

### Complete Control Loop

```{mermaid}
flowchart TB
    subgraph "Reference Generation"
        RefGen[Reference Generator<br/>Trajectory Planning]
        RefSignals[x_ref(t), θ₁_ref(t), θ₂_ref(t)<br/>ẋ_ref(t), θ̇₁_ref(t), θ̇₂_ref(t)]
    end

    subgraph "Control System"
        ErrorCalc[Error Calculation<br/>e⃗(t) = x⃗(t) - x⃗_ref(t)]

        subgraph "SMC Controller Selection"
            ClassicalSMC[Classical SMC<br/>Boundary Layer Method]
            SuperTwisting[Super-Twisting SMC<br/>Continuous Control]
            AdaptiveSMC[Adaptive SMC<br/>Parameter Estimation]
            HybridSMC[Hybrid Adaptive STA<br/>Best Performance]
        end

        SlidingSurface[Sliding Surface<br/>s(x⃗) = Sx⃗ = 0]
        ControlLaw[Control Law<br/>u = u_eq + u_sw]
    end

    subgraph "Plant Dynamics"
        PlantEq[M(q⃗)q⃗̈ + C(q⃗,q⃗̇)q⃗̇ + G(q⃗) = Bu⃗]
        StateUpdate[State Integration<br/>ẋ⃗ = f(x⃗, u)]
        OutputEq[y⃗ = Cx⃗<br/>Measured States]
    end

    subgraph "Parameter Optimization"
        PSO[PSO Optimizer<br/>Automated Tuning]
        ObjectiveFunc[J(θ) = w₁J_e + w₂J_u + w₃J_s]
        ConstraintCheck[Stability Constraints<br/>Performance Bounds]
    end

    RefGen --> RefSignals
    RefSignals --> ErrorCalc
    OutputEq --> ErrorCalc

    ErrorCalc --> ClassicalSMC
    ErrorCalc --> SuperTwisting
    ErrorCalc --> AdaptiveSMC
    ErrorCalc --> HybridSMC

    ClassicalSMC --> SlidingSurface
    SuperTwisting --> SlidingSurface
    AdaptiveSMC --> SlidingSurface
    HybridSMC --> SlidingSurface

    SlidingSurface --> ControlLaw
    ControlLaw --> PlantEq
    PlantEq --> StateUpdate
    StateUpdate --> OutputEq

    ControlLaw --> ObjectiveFunc
    ObjectiveFunc --> PSO
    PSO --> ConstraintCheck
    ConstraintCheck --> ClassicalSMC
    ConstraintCheck --> SuperTwisting
    ConstraintCheck --> AdaptiveSMC
    ConstraintCheck --> HybridSMC

    style SlidingSurface fill:#f3e5f5
    style PSO fill:#e1f5fe
    style PlantEq fill:#fff3e0
```

### Signal Flow Diagram

```{mermaid}
flowchart LR
    subgraph "Input Signals"
        RefTraj[Reference<br/>Trajectory<br/>x⃗_ref(t)]
        Disturbance[External<br/>Disturbances<br/>d⃗(t)]
    end

    subgraph "Controller Processing"
        ErrorComp[Error<br/>e⃗ = x⃗ - x⃗_ref]
        SlidingCalc[Sliding Surface<br/>s = Se⃗]
        EquivControl[Equivalent Control<br/>u_eq = (SB)⁻¹[Sf̂ - Sẋ_ref]]
        SwitchControl[Switching Control<br/>u_sw = -η sign(s)]
        ControlSum[Control Sum<br/>u = u_eq + u_sw]
    end

    subgraph "Plant Response"
        PlantDyn[Plant Dynamics<br/>ẋ⃗ = f(x⃗, u) + d⃗]
        StateOut[System State<br/>x⃗(t)]
        MeasuredOut[Measured Output<br/>y⃗ = Cx⃗ + v⃗]
    end

    subgraph "Feedback Path"
        StateFeedback[State Feedback<br/>Complete State]
        NoiseFilter[Noise Filtering<br/>Kalman Filter]
    end

    RefTraj --> ErrorComp
    MeasuredOut --> ErrorComp

    ErrorComp --> SlidingCalc
    SlidingCalc --> EquivControl
    SlidingCalc --> SwitchControl

    EquivControl --> ControlSum
    SwitchControl --> ControlSum

    ControlSum --> PlantDyn
    Disturbance --> PlantDyn
    PlantDyn --> StateOut
    StateOut --> MeasuredOut

    MeasuredOut --> NoiseFilter
    NoiseFilter --> StateFeedback
    StateFeedback --> ErrorComp

    style ErrorComp fill:#f3e5f5
    style SlidingCalc fill:#e8f5e8
    style PlantDyn fill:#e1f5fe
```

## Mathematical Representation

### State-Space Block Diagram

```{mermaid}
flowchart TB
    subgraph "State-Space Representation"
        StateEq[State Equation<br/>ẋ⃗ = [q⃗̇<br/>M⁻¹(Bu - Cq⃗̇ - G)]]
        OutputEq[Output Equation<br/>y⃗ = [x, θ₁, θ₂]ᵀ]
        StateVector[State Vector<br/>x⃗ = [x, θ₁, θ₂, ẋ, θ̇₁, θ̇₂]ᵀ]
    end

    subgraph "Matrix Components"
        MassMatrix[Inertia Matrix<br/>M(q⃗) ∈ ℝ³ˣ³<br/>Positive Definite]
        CoriolisMatrix[Coriolis Matrix<br/>C(q⃗,q⃗̇) ∈ ℝ³ˣ³<br/>Velocity Dependent]
        GravityVector[Gravity Vector<br/>G(q⃗) ∈ ℝ³<br/>Configuration Dependent]
        InputMatrix[Input Matrix<br/>B = [1, 0, 0]ᵀ]
    end

    subgraph "Properties"
        Controllability[Controllability<br/>rank(𝒞) = 6<br/>Fully Controllable]
        Observability[Observability<br/>rank(𝒪) = 6<br/>Fully Observable]
        Stability[Stability<br/>Unstable Equilibrium<br/>Requires Control]
    end

    StateVector --> StateEq
    StateEq --> OutputEq

    MassMatrix --> StateEq
    CoriolisMatrix --> StateEq
    GravityVector --> StateEq
    InputMatrix --> StateEq

    StateEq --> Controllability
    OutputEq --> Observability
    StateVector --> Stability

    style StateEq fill:#f3e5f5
    style Stability fill:#fff3e0
```

### Energy Flow Diagram

```{mermaid}
flowchart LR
    subgraph "Energy Sources"
        ElectricalEnergy[Electrical Energy<br/>Motor Input<br/>P_in = u·i]
        GravitationalPE[Gravitational PE<br/>V = mgh<br/>Conservative]
    end

    subgraph "Energy Storage"
        KineticEnergy[Kinetic Energy<br/>T = ½x⃗ᵀM(q⃗)x⃗̇<br/>Motion Energy]
        PotentialEnergy[Potential Energy<br/>V = V_gravity<br/>Position Energy]
    end

    subgraph "Energy Dissipation"
        FrictionLoss[Friction Losses<br/>P_friction = bẋ²<br/>Non-Conservative]
        ElectricalLoss[Electrical Losses<br/>Motor Inefficiency<br/>Heat Generation]
    end

    subgraph "Control Energy"
        ControlPower[Control Power<br/>P_control = u·ẋ<br/>Energy Injection]
        OptimalControl[Optimal Control<br/>Minimize Energy<br/>Subject to Performance]
    end

    ElectricalEnergy --> ControlPower
    ControlPower --> KineticEnergy
    GravitationalPE --> PotentialEnergy

    KineticEnergy --> FrictionLoss
    ElectricalEnergy --> ElectricalLoss

    ControlPower --> OptimalControl
    OptimalControl --> KineticEnergy
    OptimalControl --> PotentialEnergy

    style KineticEnergy fill:#e8f5e8
    style ControlPower fill:#f3e5f5
    style OptimalControl fill:#e1f5fe
```

## Implementation Architecture

### Software Module Hierarchy

```{mermaid}
flowchart TB
    subgraph "Application Layer"
        CLI[Command Line Interface<br/>simulate.py<br/>Main Entry Point]
        WebApp[Streamlit Web App<br/>streamlit_app.py<br/>Interactive Interface]
        JupyterNB[Jupyter Notebooks<br/>Analysis & Visualization<br/>Research Tools]
    end

    subgraph "Control Layer"
        ControlFactory[Controller Factory<br/>src.controllers.factory<br/>Dynamic Selection]

        subgraph "Controller Implementations"
            ClassicCtrl[Classical SMC<br/>src.controllers.classic_smc<br/>Boundary Layer Method]
            STACtrl[Super-Twisting SMC<br/>src.controllers.sta_smc<br/>Continuous Control]
            AdaptiveCtrl[Adaptive SMC<br/>src.controllers.adaptive_smc<br/>Parameter Estimation]
            HybridCtrl[Hybrid Adaptive STA<br/>src.controllers.hybrid_adaptive_sta_smc<br/>Best Performance]
        end
    end

    subgraph "Simulation Layer"
        SimRunner[Simulation Runner<br/>src.core.simulation_runner<br/>Integration Engine]
        SimContext[Simulation Context<br/>src.core.simulation_context<br/>State Management]
        VectorSim[Vector Simulation<br/>src.core.vector_sim<br/>Batch Processing]
    end

    subgraph "Physics Layer"
        DynamicsSimple[Simple Dynamics<br/>src.core.dynamics<br/>Linearized Model]
        DynamicsFull[Full Dynamics<br/>src.core.dynamics_full<br/>Complete Nonlinear]
        SafetyGuards[Safety Guards<br/>src.core.safety_guards<br/>Constraint Enforcement]
    end

    subgraph "Optimization Layer"
        PSOOptimizer[PSO Optimizer<br/>src.optimizer.pso_optimizer<br/>Parameter Tuning]
        CostFunctions[Cost Functions<br/>Multi-Objective Evaluation<br/>Performance Metrics]
    end

    subgraph "Infrastructure Layer"
        ConfigMgmt[Configuration Management<br/>src.config<br/>YAML + Validation]
        Protocols[Type Protocols<br/>src.core.protocols<br/>Interface Definitions]
        NumbaUtils[Numba Utilities<br/>src.core.numba_utils<br/>JIT Compilation]
    end

    CLI --> ControlFactory
    WebApp --> ControlFactory
    JupyterNB --> ControlFactory

    ControlFactory --> ClassicCtrl
    ControlFactory --> STACtrl
    ControlFactory --> AdaptiveCtrl
    ControlFactory --> HybridCtrl

    ClassicCtrl --> SimRunner
    STACtrl --> SimRunner
    AdaptiveCtrl --> SimRunner
    HybridCtrl --> SimRunner

    SimRunner --> SimContext
    SimRunner --> VectorSim
    SimContext --> DynamicsSimple
    SimContext --> DynamicsFull
    VectorSim --> NumbaUtils

    DynamicsSimple --> SafetyGuards
    DynamicsFull --> SafetyGuards

    PSOOptimizer --> CostFunctions
    PSOOptimizer --> ControlFactory

    SimRunner --> ConfigMgmt
    ControlFactory --> Protocols

    style ControlFactory fill:#f3e5f5
    style SimRunner fill:#e8f5e8
    style PSOOptimizer fill:#e1f5fe
    style ConfigMgmt fill:#fff3e0
```

### Data Flow Architecture

```{mermaid}
flowchart LR
    subgraph "Input Data"
        ConfigFile[Configuration<br/>config.yaml<br/>Parameters & Settings]
        RefTrajectory[Reference Trajectory<br/>Desired States<br/>x_ref(t), θ_ref(t)]
        InitialConditions[Initial Conditions<br/>x₀, θ₁₀, θ₂₀<br/>ẋ₀, θ̇₁₀, θ̇₂₀]
    end

    subgraph "Processing Pipeline"
        Validation[Input Validation<br/>Pydantic Models<br/>Constraint Checking]
        Simulation[Simulation Engine<br/>ODE Integration<br/>Real-time Execution]
        Optimization[Optimization Loop<br/>PSO Algorithm<br/>Parameter Search]
    end

    subgraph "Output Data"
        TimeSeriesData[Time Series<br/>States, Controls<br/>Performance Metrics]
        OptimalParams[Optimal Parameters<br/>Tuned Gains<br/>JSON Export]
        VisualizationData[Visualization<br/>Plots, Animations<br/>Analysis Reports]
    end

    subgraph "Storage & Export"
        JSONExport[JSON Files<br/>Structured Data<br/>Parameter Sets]
        CSVExport[CSV Files<br/>Time Series<br/>Numerical Data]
        PlotExport[Plot Files<br/>PNG, SVG, PDF<br/>Publication Quality]
    end

    ConfigFile --> Validation
    RefTrajectory --> Validation
    InitialConditions --> Validation

    Validation --> Simulation
    Validation --> Optimization

    Simulation --> TimeSeriesData
    Optimization --> OptimalParams
    TimeSeriesData --> VisualizationData

    TimeSeriesData --> CSVExport
    OptimalParams --> JSONExport
    VisualizationData --> PlotExport

    style Validation fill:#f3e5f5
    style Simulation fill:#e8f5e8
    style Optimization fill:#e1f5fe
```

## Performance and Scalability

### Computational Architecture

```{mermaid}
flowchart TB
    subgraph "Performance Optimization"
        JITCompilation[JIT Compilation<br/>Numba Acceleration<br/>10-100x Speedup]
        VectorizedOps[Vectorized Operations<br/>NumPy/SciPy<br/>SIMD Instructions]
        ParallelExecution[Parallel Execution<br/>Multiprocessing<br/>PSO Particles]
    end

    subgraph "Memory Management"
        EfficientStorage[Efficient Storage<br/>Structured Arrays<br/>Memory Locality]
        LazyLoading[Lazy Loading<br/>On-Demand Data<br/>Reduced Memory]
        CacheOptimization[Cache Optimization<br/>Temporal Locality<br/>Fast Access]
    end

    subgraph "Scalability Features"
        BatchProcessing[Batch Processing<br/>Multiple Simulations<br/>Parameter Sweeps]
        DistributedComputing[Distributed Computing<br/>Cluster Support<br/>MPI/Dask]
        CloudDeployment[Cloud Deployment<br/>Container Support<br/>Kubernetes Ready]
    end

    JITCompilation --> VectorizedOps
    VectorizedOps --> ParallelExecution

    EfficientStorage --> LazyLoading
    LazyLoading --> CacheOptimization

    BatchProcessing --> DistributedComputing
    DistributedComputing --> CloudDeployment

    ParallelExecution --> BatchProcessing
    CacheOptimization --> BatchProcessing

    style JITCompilation fill:#e8f5e8
    style ParallelExecution fill:#f3e5f5
    style CloudDeployment fill:#e1f5fe
```

### Real-Time Performance

```{mermaid}
flowchart LR
    subgraph "Real-Time Requirements"
        SamplingRate[Sampling Rate<br/>1 kHz Control Loop<br/>1 ms Deadline]
        LatencyBounds[Latency Bounds<br/>< 0.5 ms Processing<br/>Deterministic Response]
        ThroughputReqs[Throughput Requirements<br/>1000 samples/sec<br/>Continuous Operation]
    end

    subgraph "Performance Metrics"
        ExecutionTime[Execution Time<br/>Per Control Cycle<br/>Microsecond Precision]
        MemoryUsage[Memory Usage<br/>Peak & Average<br/>Memory Profiling]
        CPUUtilization[CPU Utilization<br/>Core Loading<br/>Thermal Management]
    end

    subgraph "Optimization Strategies"
        PreComputation[Pre-computation<br/>Lookup Tables<br/>Trigonometric Functions]
        AlgorithmTuning[Algorithm Tuning<br/>Reduced Complexity<br/>Approximate Methods]
        HardwareAccel[Hardware Acceleration<br/>GPU Computing<br/>FPGA Implementation]
    end

    SamplingRate --> ExecutionTime
    LatencyBounds --> ExecutionTime
    ThroughputReqs --> MemoryUsage

    ExecutionTime --> PreComputation
    MemoryUsage --> AlgorithmTuning
    CPUUtilization --> HardwareAccel

    PreComputation --> AlgorithmTuning
    AlgorithmTuning --> HardwareAccel

    style SamplingRate fill:#fff3e0
    style ExecutionTime fill:#f3e5f5
    style HardwareAccel fill:#e1f5fe
```

## Navigation Links

- {doc}`block_diagrams` - Control system block diagrams
- {doc}`algorithm_flowcharts` - Detailed algorithm flows
- {doc}`results_visualization` - Performance visualization
- {doc}`../theory/system_dynamics_complete` - Mathematical foundations
- {doc}`../implementation/code_documentation_index` - Code implementation