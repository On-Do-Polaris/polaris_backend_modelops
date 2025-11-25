## 기후변화 시나리오 API 전체 가이드 (완전판)

### API 이용 정보

- **일 최대호출용량**: 일 2TB
- **사용기간**: 2025.11.11. ~ 11.18.
- **인증키**: -QzuK4QnT16M7iuEJ09eIQ

### API 호출 URL 예시

**1. SSP-SKOREA (SSP 시나리오 한반도)**

```
https://apihub-org.kma.go.kr/api/typ01/url/ssp_skorea_file_down.php?rpt=SSP585&model=5ENSMN&elem=TA&grid=gridraw&time_rsltn=daily&st_year=2021&ed_year=2030&frmat=asc&authKey=-QzuK4QnT16M7iuEJ09eIQ
```

**2. MK-PRISM (과거 격자기후자료)**

```
https://apihub-org.kma.go.kr/api/typ01/url/mkprism_file_down.php?rpt=MKPRISM&model=MKPRISMv21&elem=RN&grid=gridraw&time_rsltn=daily&st_year=2000&ed_year=2019&frmat=asc&authKey=-QzuK4QnT16M7iuEJ09eIQ
```

**3. RCP-SKOREA (RCP 시나리오 한반도)**

```
https://apihub-org.kma.go.kr/api/typ01/url/rcp_skorea_file_down.php?rpt=IC2RCP45&model=HadGEM3RA&elem=RN&grid=gridsub&time_rsltn=daily&st_year=2021&ed_year=2030&frmat=asc&authKey=-QzuK4QnT16M7iuEJ09eIQ
```

**4. SRES-SKOREA (SRES 시나리오 한반도)**

```
https://apihub-org.kma.go.kr/api/typ01/url/sres_skorea_file_down.php?rpt=SRESA1B&model=MM5&elem=TAMIN&grid=gridraw&time_rsltn=daily&st_year=2000&ed_year=2100&frmat=asc&authKey=-QzuK4QnT16M7iuEJ09eIQ
```

---

## 1. 기후변화 시나리오 (rpt 인자)

### SSP 시나리오

- **SSP1-2.6**: SSP126 (저탄소 시나리오)
- **SSP2-4.5**: SSP245 (중간 시나리오)
- **SSP3-7.0**: SSP370 (고탄소 시나리오)
- **SSP5-8.5**: SSP585 (최악 시나리오)
- **과거 모의자료**: HIST

### RCP 시나리오 (200년 제어적분)

- **과거 모의자료**: IC2HIST
- **RCP2.6**: IC2RCP26
- **RCP4.5**: IC2RCP45
- **RCP6.0**: IC2RCP60
- **RCP8.5**: IC2RCP85

### RCP 시나리오 (400년 제어적분)

- **과거 모의자료**: IC4HIST
- **RCP2.6**: IC4RCP26
- **RCP4.5**: IC4RCP45
- **RCP6.0**: IC4RCP60
- **RCP8.5**: IC4RCP85

### CLIM

- **응용지수 과거기후값**: CLIM

### SRES 시나리오

- **20C3M**: SRES20C3M
- **A2**: SRESA2
- **A1B**: SRESA1B
- **B1**: SRESB1

### 과거자료 (격자기후자료)

- **MK-PRISM(ver 1.1)**: MKPRISMv11
- **MK-PRISM(ver 1.2)**: MKPRISMv12
- **MK-PRISM(ver 2.1)**: MKPRISMv21

---

## 2. 기후요소 (elem 인자)

### 기본요소 - 대기

- **평균기온**: TA (℃)
- **최고기온**: TAMAX (℃)
- **최저기온**: TAMIN (℃)
- **강수량**: RN (mm)
- **상대습도**: RHM (%)
- **평균풍속**: WS (m/s)
- **최대풍속**: WSMAX (m/s)
- **일사량**: SI (MJ/㎡) \*RCP 시나리오는 W/㎡
- **해면기압**: PS (hPA)
- **현지기압**: PA (hPA)
- **적설량**: SD (kg/㎡)

### 기본요소 - 해양

- **해수면온도**: SST (℃)
- **표층염분**: SALNT (psu)
- **해빙면적**: SICONCA (%)
- **해수면고도**: SLR (m)

---

## 3. 극한기후지수

### 고온관련 지수

- **열대야일수**: TR25 (일) - 일 최저기온 25℃ 이상
- **폭염일수**: HW33 (일) - 일 최고기온 33℃ 이상
- **여름일수**: SU25 (일) - 일 최고기온 25℃ 이상
- **식물성장가능기간**: GSL (일)
- **일교차**: DTR (℃)
- **온난일**: TX90P (일) - 일 최고기온 90퍼센타일 초과
- **온난일 계속기간**: WSDI (일)
- **최대온난일 계속기간**: WSDIx (일)
- **온난야**: TN90P (일) - 일 최저기온 90퍼센타일 초과
- **일최고기온 연최소**: TXn (℃)
- **일최고기온 연최대**: TXx (℃)
- **일최저기온 연최소**: TNn (℃)
- **일최저기온 연최대**: TNx (℃)

### 저온관련 지수

- **서리일수**: FD0 (일) - 일 최저기온 0℃ 미만
- **결빙일수**: ID0 (일) - 일 최고기온 0℃ 미만
- **한파일수**: CWm12 (일) - 일 최저기온 -12℃ 미만
- **한랭일**: TX10P (일) - 일 최고기온 10퍼센타일 미만
- **한랭야 계속기간**: CSDI (일)
- **최대한랭야 계속기간**: CSDIx (일)
- **한랭야**: TN10P (일) - 일 최저기온 10퍼센타일 미만

### 강수관련 지수

- **강수강도**: SDII (mm/일)
- **호우일수**: RAIN80 (일) - 일 강수량 80mm 이상
- **최대무강수 지속기간**: CDD (일)
- **1일 최다강수량**: RX1DAY (mm)
- **5일 최다강수량**: RX5DAY (mm)
- **95퍼센타일 강수일수**: RD95P (일)
- **99퍼센타일 강수일수**: RD99P (일)

---

## 4. 부문별 응용지수

### 농업 부문

| 인자명 | 설명                  | RCP | SSP |
| :----- | :-------------------- | :-- | :-- |
| GDD5   | 생육온도일수(5℃)      | ○   | ○   |
| GDD10  | 생육온도일수(10℃)     | ○   | ○   |
| GDD15  | 생육온도일수(15℃)     | ○   | ○   |
| EAT5   | 유효적산온도(5℃)      | ○   | ○   |
| EAT10  | 유효적산온도(10℃)     | ○   | ○   |
| EAT15  | 유효적산온도(15℃)     | ○   | ○   |
| PLP    | 식물기간              | ○   | ○   |
| CPP    | 작물기간              | ○   | ○   |
| FRF    | 무상기간              | ○   | -   |
| CHP    | 저온축적값 ChillUnits | ○   | ○   |
| CHA    | 고온축적값 ChillUnits | ○   | ○   |
| CPI    | 기후생산력지수        | ○   | -   |
| THI    | 온습도지수            | ○   | ○   |
| RET    | 기준증발산량          | ○   | -   |
| HDD    | 난방도일              | ○   | ○   |
| CDDs   | 냉방도일              | ○   | ○   |
| LWD    | 엽면수분지속시간      | ○   | -   |

### 산림 부문

| 인자명 | 설명               | RCP | SSP |
| :----- | :----------------- | :-- | :-- |
| MTCI   | 최저기온지수       | ○   | ○   |
| All    | 건조지수           | ○   | ○   |
| PEI    | 유효강우지수       | ○   | ○   |
| PEISPR | 유효강우지수(봄)   | ○   | ○   |
| PEISUM | 유효강우지수(여름) | ○   | ○   |
| PEIAUT | 유효강우지수(가을) | ○   | ○   |
| PEIWIN | 유효강우지수(겨울) | ○   | ○   |

### 동물생태 부문

| 인자명 | 설명               | RCP | SSP |
| :----- | :----------------- | :-- | :-- |
| EIWW   | 물새류월동환경지수 | ○   | ○   |
| CCSI   | 기후변화심각도지수 | ○   | ○   |
| OI     | 강우열량지수       | ○   | ○   |
| IOS2   | 여름철강우열량지수 | ○   | ○   |

### 보건 부문

| 인자명  | 설명                    | RCP | SSP |
| :------ | :---------------------- | :-- | :-- |
| HI      | 열지수                  | ○   | ○   |
| DI      | 불쾌지수                | ○   | ○   |
| AT      | 체감온도                | ○   | ○   |
| ATw     | 체감온도(겨울철)        | ○   | -   |
| ATs     | 체감온도(여름철)        | ○   | -   |
| HHSI    | 열사병발생위험지수      | ○   | ○   |
| HMDX    | 열체감지수(Humidex)     | ○   | ○   |
| WDCH    | 체감추위지수(Windchill) | ○   | -   |
| NET     | 평균온도 NET            | ○   | ○   |
| NETMAX  | 최고기온 NET            | ○   | ○   |
| NETMIN  | 최저기온 NET            | ○   | ○   |
| WBGT    | 온열지수(평균)          | ○   | -   |
| WBGTMAX | 온열지수(최고)          | ○   | -   |

### 방재 부문

| 인자명 | 설명                          | RCP | SSP |
| :----- | :---------------------------- | :-- | :-- |
| SPI3   | 표준강수지수(3개월)           | ○   | ○   |
| SPI6   | 표준강수지수(6개월)           | ○   | ○   |
| SPI9   | 표준강수지수(9개월)           | ○   | ○   |
| SPI12  | 표준강수지수(12개월)          | ○   | ○   |
| HPNPRD | 독립호우사상 - 지속기간       | ○   | ○   |
| HPNMAX | 독립호우사상 - 호우총량(최대) | ○   | ○   |
| HPNAVG | 독립호우사상 - 호우총량(평균) | ○   | ○   |
| SPEI3  | 표준강수증발산지수(3개월)     | -   | ○   |
| SPEI6  | 표준강수증발산지수(6개월)     | -   | ○   |
| SPEI9  | 표준강수증발산지수(9개월)     | -   | ○   |
| SPEI12 | 표준강수증발산지수(12개월)    | -   | ○   |

### 수자원 부문 (RCP 200년 제어적분 자료만 제공)

| 인자명 | 설명               | RCP | SSP |
| :----- | :----------------- | :-- | :-- |
| PET    | 잠재증발산량       | ○   | ○   |
| FD     | 유황(중권역)       | ○   | -   |
| RO     | 유출량(중권역)     | ○   | -   |
| PET    | 잠재증발산량(지점) | ○   | -   |
| RN     | 강수량(중권역)     | ○   | ○   |

---

## 5. 공간해상도 (grid 인자)

### 격자 및 행정구역

**gridraw (격자)**

- 적용 시나리오: 전체
- 영역: korea, skorea
- 요소: 기본, 극한기후지수, 응용지수

**sido17 (17개 광역지자체)**

- 적용 시나리오: IC2RCP, IC4RC, MKPRISM
- 영역: korea, skorea
- 요소: 기본, 극한기후지수, 응용지수

**sgg113 (113개 기초지자체)**

- 적용 시나리오: IC2RCP45, IC2RCP85
- 영역: korea
- 요소: FD, PET, RN, RO

**sgg230 (230개 기초지자체)**

- 적용 시나리오: CLIM, IC2HIST, IC2RCP45, IC2RCP85, IC4RCP
- 영역: korea, skorea
- 요소: 기본, 극한기후지수, 응용지수 중 일부

**sgg231 (231개 기초지자체)**

- 적용 시나리오: IC2RCP45, IC2RCP85
- 영역: korea
- 요소: EIWW

**sgg237 (237개 기초지자체)**

- 적용 시나리오: IC4RCP, MKPRISMv11
- 영역: korea, skorea
- 요소: 기본, 극한기후지수, 응용지수

**sgg261 (261개 기초지자체)**

- 적용 시나리오: SSP, MKPRISMv21
- 영역: skorea
- 요소: 기본, 극한기후지수, 응용지수

### 읍면동

**dong3501 (3,501개 읍면동)**

- 적용 시나리오: SSP, MKPRISMv21
- 영역: skorea
- 요소: 기본, 극한기후지수, 응용지수

**dong3550 (3,550개 읍면동)**

- 적용 시나리오: IC4RCP, MKPRISMv11
- 영역: skorea
- 요소: 기본, 극한기후지수

### 관측지점

**stn66 (66개 관측지점)**

- 적용 시나리오: IC4RCP
- 영역: skorea
- 요소: SPI3, SPI6, SPI9, SPI12
- 상세 지점정보: 별첨 참조[^11]

**stn72 (72개 관측지점)**

- 적용 시나리오: IC4RCP
- 영역: skorea
- 요소: HPN
- 상세 지점정보: 별첨 참조[^11]

**stn73 (73개 관측지점)**

- 적용 시나리오: IC2HIST, IC2RCP45, IC2RCP85, IC4RCP
- 영역: korea, skorea
- 요소: 기본, 극한기후지수, 응용지수 중 일부
- 상세 지점정보: 별첨 참조[^11]

### 유역

**bbsn21 (대권역 21개)**

- 적용 시나리오: SSP, MKPRISMv21
- 영역: skorea
- 요소: RN, TA, TAMAX, TAMIN, WS
- 상세 지점정보: 별첨 참조[^11]

**kmabbsn26 (KMA 대권역 26개)**

- 상세 지점정보: 별첨 참조[^11]

**mbsn112 (중권역 112개)**

- 상세 지점정보: 별첨 참조[^11]

**sbsn813 (표준유역 813개)**

- 상세 지점정보: 별첨 참조[^11]

**asos95 (95개 관측지점)**

- 적용 시나리오: SSP, MKPRISMv21
- 영역: skorea
- 요소: RHM, RN, SI, TA, TAMAX, TAMIN, WS
- 상세 지점정보: 별첨 참조[^12]

---

## 6. 시간해상도 (time_rsltn 인자)

- **yearly**: 연별 데이터
- **monthly**: 월별 데이터
- **daily**: 일별 데이터

---

## 7. 자료 형태/포맷 (frmat 인자)

- **asc**: ASCII 형식
- **nc**: NetCDF 형식

---

## 8. 추가 파라미터

### 모델 (model 인자)

- **5ENSMN**: SSP 시나리오용 5개 앙상블 평균
- **MKPRISMv21**: MK-PRISM 버전 2.1
- **HadGEM3RA**: RCP 시나리오용 영국기상청 모델
- **MM5**: SRES 시나리오용 모델

### 연도 범위

- **st_year**: 시작 연도
- **ed_year**: 종료 연도

### 인증 (authKey)

- API 호출 시 필수 파라미터
- 예시: -QzuK4QnT16M7iuEJ09eIQ

---

이 가이드는 기상청 API허브에서 제공하는 기후변화 시나리오 데이터를 조회하고 다운로드하기 위한 완전한 참조 문서입니다. URL 파라미터를 조합하여 원하는 시나리오, 기후요소, 공간/시간 해상도의 데이터를 획득할 수 있습니다.[^1][^2][^13]
<span style="display:none">[^10][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>
