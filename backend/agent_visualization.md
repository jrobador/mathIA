```mermaid
---
config:
  layout: elk
---
flowchart TD
    Start(["BEGIN"]) --> DetermineNextStep{"determine_next_step"}
    DetermineNextStep -- "waiting_for_input == true" --> PauseExecution["Pause execution (return empty dict)"]
    DetermineNextStep -- "mastery < 0.3 & !theory_presented" --> PresentTheory["present_theory"]
    DetermineNextStep -- "mastery < 0.3 & theory_presented" --> PresentGuidedPractice["present_guided_practice"]
    DetermineNextStep -- "0.3 <= mastery <= 0.7" --> PresentIndependentPractice["present_independent_practice"]
    DetermineNextStep -- "last_eval == INCORRECT_CONCEPTUAL" --> ProvideFeedback["provide_targeted_feedback"]
    DetermineNextStep -- "last_eval == INCORRECT_CALCULATION" --> ProvideFeedback
    DetermineNextStep -- "consecutive_incorrect >= 3" --> SimplifyInstruction["Simplify or return to theory"]
    DetermineNextStep -- "(mastery > 0.6 & consecutive_correct >= 2) OR (mastery > 0.8 & consecutive_correct >= 1)" --> CheckAdvance{"check_advance_topic"}
    DetermineNextStep -- "Default case (no other conditions met)" --> PresentIndependentPractice
    
    PresentTheory -- "Generate theory text, image, audio and update state" --> DetermineNextStep
    PresentGuidedPractice -- "Generate practice problem, image, audio and set last_problem_details" --> SetWaitFlag1["Set waiting_for_input = true"]
    PresentIndependentPractice -- "Generate practice problem, image, audio and set last_problem_details" --> SetWaitFlag2["Set waiting_for_input = true"]
    SetWaitFlag1 --> DetermineNextStep
    SetWaitFlag2 --> DetermineNextStep
    
    PauseExecution -- "Wait for API to send input" --> APIReceivesInput["API receives user input"]
    APIReceivesInput -- "Clear waiting_for_input flag" --> EvaluateAnswer["evaluate_answer"]
    EvaluateAnswer -- "Update mastery, counters and generate audio feedback" --> AutoDetermineNext["Automatically call determine_next_step"]
    AutoDetermineNext --> DetermineNextStep
    
    ProvideFeedback -- "Generate feedback text, image if conceptual, audio, update count" --> DetermineNextStep
    SimplifyInstruction -- "May reduce mastery, adjust CPA phase, generate audio" --> DetermineNextStep
    
    CheckAdvance -- "Next topic exists" --> NextTopic["Update topic, reset CPA to Concrete, reset counters, generate audio"]
    CheckAdvance -- "No more topics" --> EndGraph(["FIN"])
    NextTopic --> DetermineNextStep
    
    subgraph Azure Services Integration
      GenerateImage["generate_image 
                    (Azure DALL-E)"]
      GenerateSpeech["generate_speech 
                    (Azure Speech)"]
      InvokeLLM["invoke_with_prompty 
      (Azure OpenAI)"]
    end
    
    PresentTheory -.-> InvokeLLM
    PresentGuidedPractice -.-> InvokeLLM
    PresentIndependentPractice -.-> InvokeLLM
    ProvideFeedback -.-> InvokeLLM
    EvaluateAnswer -.-> InvokeLLM
    
    PresentTheory -.-> GenerateImage
    PresentGuidedPractice -.-> GenerateImage
    PresentIndependentPractice -.-> GenerateImage
    ProvideFeedback -.-> GenerateImage
    
    PresentTheory -.-> GenerateSpeech
    PresentGuidedPractice -.-> GenerateSpeech
    PresentIndependentPractice -.-> GenerateSpeech
    ProvideFeedback -.-> GenerateSpeech
    EvaluateAnswer -.-> GenerateSpeech
    SimplifyInstruction -.-> GenerateSpeech
    NextTopic -.-> GenerateSpeech
     
    classDef decision fill:#f9f,stroke:#333,stroke-width:2px
    classDef process fill:#bbf,stroke:#333,stroke-width:1px
    classDef waiting fill:#fcf,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5
    classDef terminator fill:#bfb,stroke:#333,stroke-width:1px,border-radius:10px
    classDef subProcess fill:#ffe,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5
    classDef apiProcess fill:#fcc,stroke:#333,stroke-width:1px
    classDef services fill:#d9f3ff,stroke:#0077be,stroke-width:1px
    
    Start:::terminator
    DetermineNextStep:::decision
    PauseExecution:::waiting
    PresentTheory:::process
    PresentGuidedPractice:::process
    PresentIndependentPractice:::process
    ProvideFeedback:::process
    SimplifyInstruction:::process
    CheckAdvance:::decision
    SetWaitFlag1:::waiting
    SetWaitFlag2:::waiting
    APIReceivesInput:::apiProcess
    EvaluateAnswer:::process
    AutoDetermineNext:::apiProcess
    NextTopic:::process
    EndGraph:::terminator
    GenerateImage:::services
    GenerateSpeech:::services
    InvokeLLM:::services
    Azure:::services