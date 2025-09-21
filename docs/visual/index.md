# Visual Documentation

```{toctree}
:maxdepth: 2
:hidden:

system_diagrams
block_diagrams
algorithm_flowcharts
results_visualization
```

This section provides comprehensive visual documentation including system diagrams, control flow charts, optimization workflows, and result analysis visualizations.

## Contents

::::{grid} 2
:::{grid-item-card} **System Diagrams**
:link: system_diagrams
:link-type: doc

Physical system representation, coordinate frames, and plant-controller relationships.
:::

:::{grid-item-card} **Block Diagrams**
:link: block_diagrams
:link-type: doc

Control system block diagrams, signal flow, and feedback loops.
:::

:::{grid-item-card} **Algorithm Flowcharts**
:link: algorithm_flowcharts
:link-type: doc

Step-by-step algorithm flows for controllers and optimization procedures.
:::

:::{grid-item-card} **Results Visualization**
:link: results_visualization
:link-type: doc

Templates and examples for plotting simulation results and performance analysis.
:::
::::

## System Overview

### Double-Inverted Pendulum Architecture

```{mermaid}
flowchart TB
    subgraph "Physical System"
        Cart[Cart<br/>Mass: m₀]
        Pend1[Pendulum 1<br/>Mass: m₁, Length: l₁]
        Pend2[Pendulum 2<br/>Mass: m₂, Length: l₂]

        Cart -.->|θ₁| Pend1
        Pend1 -.->|θ₂| Pend2
    end

    subgraph "Sensing"
        PosSensor[Position Sensor<br/>x, θ₁, θ₂]
        VelSensor[Velocity Sensor<br/>ẋ, θ̇₁, θ̇₂]
    end

    subgraph "Control System"
        Controller[SMC Controller<br/>Classical/STA/Adaptive]
        Actuator[Force Actuator<br/>u(t)]
    end

    subgraph "Optimization"
        PSO[PSO Optimizer<br/>Gain Tuning]
        CostFunc[Cost Function<br/>J(θ)]
    end

    Cart --> PosSensor
    Cart --> VelSensor
    PosSensor --> Controller
    VelSensor --> Controller
    Controller --> Actuator
    Actuator -->|Force u| Cart

    Controller --> CostFunc
    CostFunc --> PSO
    PSO -->|Optimized Gains| Controller

    style Cart fill:#e1f5fe
    style Controller fill:#f3e5f5
    style PSO fill:#e8f5e8
```

### Control System Signal Flow

```{mermaid}
flowchart LR
    subgraph "Reference Generation"
        RefGen[Reference<br/>Generator]
        RefTraj[xᵣₑf, θ₁ᵣₑf, θ₂ᵣₑf]
    end

    subgraph "Feedback Control"
        Sum1[Σ]
        Error[Error<br/>e = x - xᵣₑf]
        SMC[SMC<br/>Controller]
        Plant[DIP<br/>System]
        StateOut[State<br/>x, θ₁, θ₂, ẋ, θ̇₁, θ̇₂]
    end

    subgraph "Performance Analysis"
        Metrics[Performance<br/>Metrics]
        Cost[Cost<br/>Function]
    end

    RefGen --> RefTraj
    RefTraj --> Sum1
    StateOut --> Sum1
    Sum1 --> Error
    Error --> SMC
    SMC -->|Control u| Plant
    Plant --> StateOut

    StateOut --> Metrics
    Error --> Cost
    SMC --> Cost

    style SMC fill:#f3e5f5
    style Plant fill:#e1f5fe
    style Cost fill:#fff3e0
```

## Mathematical Visualization

### Phase Portrait Template

```{mermaid}
flowchart TD
    subgraph "Phase Space Analysis"
        PhaseSpace[Phase Portrait<br/>θ₁ vs θ̇₁]
        Trajectory[System Trajectories]
        SlidingSurface[Sliding Surface<br/>s(x) = 0]
        Equilibrium[Equilibrium Points]
    end

    subgraph "Stability Analysis"
        Lyapunov[Lyapunov Function<br/>V(x)]
        EnergyContours[Energy Contours]
        ReachingLaw[Reaching Law<br/>ṡ ≤ -η|s|]
    end

    PhaseSpace --> Trajectory
    PhaseSpace --> SlidingSurface
    PhaseSpace --> Equilibrium

    Lyapunov --> EnergyContours
    Lyapunov --> ReachingLaw

    style SlidingSurface fill:#f3e5f5
    style Equilibrium fill:#e8f5e8
```

### Optimization Workflow

```{mermaid}
flowchart TB
    Start([Start PSO<br/>Optimization])

    subgraph "Initialization"
        InitSwarm[Initialize Particle Swarm<br/>N particles, random positions]
        SetBounds[Set Parameter Bounds<br/>θₘᵢₙ ≤ θ ≤ θₘₐₓ]
    end

    subgraph "Evaluation Loop"
        EvalFitness[Evaluate Fitness<br/>J(θᵢ) for each particle]
        RunSim[Run Simulation<br/>with parameters θᵢ]
        CalcCost[Calculate Cost<br/>J = wₑIₑ + wᵤIᵤ + wₛIₛ]
    end

    subgraph "PSO Update"
        UpdatePersonal[Update Personal Best<br/>pᵢ = arg min J(θ)]
        UpdateGlobal[Update Global Best<br/>g = arg min J(θ)]
        UpdateVelocity[Update Velocity<br/>vᵢ⁽ᵏ⁺¹⁾ = w·vᵢ⁽ᵏ⁾ + c₁r₁(pᵢ-xᵢ) + c₂r₂(g-xᵢ)]
        UpdatePosition[Update Position<br/>xᵢ⁽ᵏ⁺¹⁾ = xᵢ⁽ᵏ⁾ + vᵢ⁽ᵏ⁺¹⁾]
    end

    CheckConv{Convergence?<br/>|g⁽ᵏ⁺¹⁾ - g⁽ᵏ⁾| < ε}
    MaxIter{Max Iterations?<br/>k ≥ kₘₐₓ}

    End([Return Optimal<br/>Parameters θ*])

    Start --> InitSwarm
    InitSwarm --> SetBounds
    SetBounds --> EvalFitness
    EvalFitness --> RunSim
    RunSim --> CalcCost
    CalcCost --> UpdatePersonal
    UpdatePersonal --> UpdateGlobal
    UpdateGlobal --> UpdateVelocity
    UpdateVelocity --> UpdatePosition
    UpdatePosition --> CheckConv

    CheckConv -->|No| MaxIter
    MaxIter -->|No| EvalFitness
    MaxIter -->|Yes| End
    CheckConv -->|Yes| End

    style InitSwarm fill:#e8f5e8
    style EvalFitness fill:#fff3e0
    style UpdateVelocity fill:#f3e5f5
    style End fill:#e1f5fe
```

## Implementation Architecture

### Software Stack

```{mermaid}
flowchart TB
    subgraph "User Interfaces"
        CLI[Command Line<br/>simulate.py]
        Web[Web Interface<br/>Streamlit App]
        Jupyter[Jupyter Notebooks<br/>Analysis & Visualization]
    end

    subgraph "Application Layer"
        SimRunner[Simulation Runner<br/>Orchestration]
        ControlFactory[Controller Factory<br/>Dynamic Selection]
        ConfigMgr[Configuration<br/>Management]
    end

    subgraph "Core Engine"
        Dynamics[System Dynamics<br/>Nonlinear Models]
        Controllers[SMC Controllers<br/>Control Algorithms]
        Optimizer[PSO Optimizer<br/>Parameter Tuning]
    end

    subgraph "Computational Backend"
        NumPy[NumPy<br/>Array Operations]
        SciPy[SciPy<br/>Integration & Optimization]
        Numba[Numba<br/>JIT Compilation]
        Matplotlib[Matplotlib<br/>Visualization]
    end

    CLI --> SimRunner
    Web --> SimRunner
    Jupyter --> SimRunner

    SimRunner --> ControlFactory
    SimRunner --> ConfigMgr
    ControlFactory --> Controllers

    Controllers --> Dynamics
    Controllers --> Optimizer

    Dynamics --> NumPy
    Controllers --> SciPy
    Optimizer --> Numba
    SimRunner --> Matplotlib

    style CLI fill:#e8f5e8
    style Controllers fill:#f3e5f5
    style Numba fill:#fff3e0
```

## Performance Visualization Templates

### Typical Simulation Results

The following templates show the standard visualizations generated by the system:

1. **Time Domain Response**
   - State trajectories: $x(t)$, $\theta_1(t)$, $\theta_2(t)$
   - Control input: $u(t)$
   - Tracking errors: $e(t)$

2. **Phase Portraits**
   - State space trajectories
   - Sliding surface visualization
   - Lyapunov function contours

3. **Performance Metrics**
   - Settling time analysis
   - Overshoot measurements
   - Control effort quantification
   - Chattering analysis

4. **Optimization Convergence**
   - PSO swarm evolution
   - Cost function convergence
   - Parameter sensitivity analysis

For detailed implementation examples, see {doc}`results_visualization`.

## Interactive Elements

### Real-time Visualization

The Streamlit interface provides real-time visualization capabilities:

- **Live simulation plotting** with parameter adjustment
- **Interactive phase portraits** with zoom and pan
- **Real-time performance metrics** updates
- **Comparative analysis** between different controllers

### 3D Visualizations

For enhanced understanding, the system includes 3D visualizations:

- **3D pendulum animation** showing physical motion
- **3D phase space** for complete state visualization
- **Surface plots** for cost function landscapes

See {doc}`../implementation/examples/visualization_tutorial` for implementation details.

---

**Navigation:**
- {doc}`system_diagrams` - Detailed system representations
- {doc}`block_diagrams` - Control system diagrams
- {doc}`algorithm_flowcharts` - Algorithm implementations
- {doc}`results_visualization` - Plotting and analysis tools