# Informal Notes - Science Vibing Sessions

## Context for Future Sessions

### User's Research Profile
- **Main focus**: Computational neuroscience for epilepsy
- **Data**: Works with sEEG, EEG, LFP recordings from epilepsy patients
- **Methods**: Heavy on signal processing (wavelets, FFT, connectivity), dynamical systems (Koopman, attractors), and physics-informed ML (SINDy, Neural ODEs)
- **Goal**: Seizure prediction, epileptogenic zone localization

### Key Preferences
1. **NO HALLUCINATED PAPERS** - User got frustrated with made-up citations
2. High-impact journals matter (Nature, Science, Brain, Epilepsia)
3. Prioritize highly-cited papers but also catch important recent work
4. User has library access - don't worry about paywalls

### Researchers They Follow
- **Computational**: Viktor Jirsa (VEP/Epileptor), Steven Brunton (SINDy), Christophe Bernard
- **Clinical**: Dario Englot, Jorge Gonzalez-Martinez, Gregory Worrell, Fabrice Bartolomei
- **Control/ML**: Sridevi Sarma, William Stacey
- **Causality**: Jakob Runge

### Literature Folder Organization
Configure your literature paths in `config/local_paths.json`:
- `NeuroDynamics/literature/` - General computational neuro
- `seizure_dynamics/literature/` - Epilepsy-specific papers
- Organized by method: SymbReg_*, DynSys_*, PhysML_*, etc.

### Topics They Care About
1. **Hankel matrices** and delay embeddings for time series
2. **Koopman operator** theory for linearizing nonlinear dynamics
3. **SINDy** and data-driven discovery
4. **Virtual brain twins** and personalized epilepsy models
5. **Connectivity measures** (PLV, wPLI, coherence) for seizure networks
6. **Tensor methods** for multi-channel data
7. **Critical slowing down** and early warning signals

### Communication Style
- Likes short, direct answers
- Appreciates knowing when you're uncertain
- Values citations and real papers over speculation
- Technical depth is good - they understand the math

### Safety Concerns
- Don't bombard APIs with requests
- Respect rate limits
- Cache results to avoid redundant calls
- Log everything for debugging

### Future Improvements They Mentioned
- Eventually add local PDF search
- Maybe integrate with their Zotero/reference manager
- Interest in Papers with Code for reproducibility

---
**Bottom line**: When in science mode, ALWAYS search for real papers first. User values accuracy over speed. Better to say "let me find sources" than to make stuff up.