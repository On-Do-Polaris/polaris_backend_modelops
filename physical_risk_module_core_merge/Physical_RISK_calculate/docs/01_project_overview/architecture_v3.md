<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# 아니 네가 이렇게 넣으면 내가 그대로 복사 붙여넣기를 못하잖아.

md 형식으로 출력해서 주면 어떻게 해

아, 불편을 드려 죄송합니다! **Markdown(`.md`)** 파일로 바로 저장하실 수 있도록, **코드 블록** 안에 깔끔하게 넣어드리겠습니다.

아래 박스 우측 상단의 **`Copy`** 버튼을 눌러서 복사한 뒤, 메모장이나 VS Code에 붙여넣고 **`workflow.md`** 라는 이름으로 저장하시면 됩니다.

```markdown
# TCFD 물리적 리스크 평가 워크플로우

```mermaid
config:
flowchart:
curve: basis
graph TB;
%% ===== 추가 데이터 전처리 =====
subgraph PreProcess[" 추가 데이터 전처리 (워크플로우 외부)"]
direction TB
UserData[["사용자 입력<br/>(additional_data)"]]
Helper["AdditionalDataHelper<br/>(LLM 1회 호출)"]
Guidelines{{"가이드라인 생성<br/>(4개 Agent)"}}

        UserData --> Helper
        Helper --> Guidelines
    end
    
    %% ===== 메인 워크플로우 =====
    subgraph MainFlow[" 메인 워크플로우 (LangGraph)"]
        direction TB
        
        Start(["__start__"])
        DC["1. Data Collection"]
        
        subgraph Parallel1["병렬 실행 (ModelOps)"]
            PRS["2. Physical Risk Score<br/>(H×E×V)"]
            AAL["3. AAL Analysis<br/>(P×D)"]
        end
        
        RI["4. Risk Integration"]
        
        subgraph Parallel2["Fork-Join 병렬"]
            BC["BC. Building Characteristics<br/>(LLM 정성 분석)"]
            
            subgraph ReportChain["Report Chain"]
                RT["5. Report Template"]
                IA["6. Impact Analysis"]
                SG["7. Strategy Generation"]
                RG["8. Report Generation"]
            end
        end
        
        Val["9. Validation<br/>(Report + BC 통합 검증)"]
        Fin["10. Finalization"]
        End(["__end__"])
        
        Start --> DC
        DC --> PRS
        DC --> AAL
        PRS --> RI
        AAL --> RI
        RI --> BC
        RI --> RT
        RT --> IA
        IA --> SG
        SG --> RG
        BC --> Val
        RG --> Val
        Val -->|"통과"| Fin
        Val -.->|"BC 이슈"| BC
        Val -.->|"Impact 이슈"| IA
        Val -.->|"Strategy 이슈"| SG
        Fin --> End
    end
    
    %% ===== 가이드라인 주입 (점선) =====
    Guidelines -.->|"가이드라인 주입<br/>(relevance ≥ 0.4)"| BC
    Guidelines -.->|"가이드라인 주입"| IA
    Guidelines -.->|"가이드라인 주입"| SG
    Guidelines -.->|"가이드라인 주입"| RG
    
    %% 스타일
    classDef preprocessing fill:#e1f5ff,stroke:#0288d1,stroke-width:3px
    classDef guideline fill:#fff9c4,stroke:#fbc02d,stroke-width:3px
    classDef main fill:#f2f0ff,stroke:#7c4dff,stroke-width:2px
    classDef parallel fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    
    class UserData,Helper preprocessing
    class Guidelines guideline
    class Start,DC,RI,Val,Fin,End main
    class PRS,AAL,BC,RT,IA,SG,RG parallel
    ```
```

<span style="display:none">[^1][^2][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://kdhyo98.tistory.com/86

[^2]: https://docs.github.com/ko/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams

[^3]: https://sabarada.tistory.com/209

[^4]: https://nahwasa.com/entry/깃허브-인텔리제이-마크다운md에-다이어그램mermaid-넣기

[^5]: https://duhui99.tistory.com/31

[^6]: https://claremont.tistory.com/entry/웹-개발-Mermaid-다이어그램을-활용합시다

[^7]: https://wikidocs.net/287759

[^8]: https://green1229.tistory.com/558

[^9]: https://publish.obsidian.md/andrea9292/2+Area/생산성+도구/Obsidian+이야기/그리면서+따라하는+Mermaid+연습

