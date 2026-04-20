# Báo cáo Lab Quan sát (Observability) Ngày 13

> **Hướng dẫn**: Điền vào tất cả các phần bên dưới. Báo cáo này được thiết kế để được phân tích bởi trợ lý chấm điểm tự động. Đảm bảo tất cả các thẻ (ví dụ: `[GROUP_NAME]`) được giữ nguyên.

## 1. Thông tin Nhóm

- [GROUP_NAME]: C401-F3
- [REPO_URL]: https://github.com/Applied-AI-Talent-Program-C401-F3/Lab13-Observability.git
- [MEMBERS]:
  - Thành viên A: Lương Trung Kiên | Vai trò: Logging & PII
  - Thành viên B: Lưu Lê Gia Bảo | Vai trò: Tracing & Enrichment
  - Thành viên C: Khương Hải Lâm | Vai trò: SLO & Alerts
  - Thành viên D: Hoàng Quốc Hùng | Vai trò: Load Test & Incident Injection
  - Thành viên E: Thái Doãn Minh Hải | Vai trò: Dashboard & Evidence
  - Thành viên F: Đặng Tuấn Anh | Vai trò: Blueprint & Demo Lead

---

## 2. Hiệu suất Nhóm (Xác minh Tự động)

- [VALIDATE_LOGS_FINAL_SCORE]: 100/100
- [TOTAL_TRACES_COUNT]: 25
- [PII_LEAKS_FOUND]: 0

---

## 3. Bằng chứng Kỹ thuật (Nhóm)

### 3.1 Logging & Tracing

- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: docs/screenshots/correlation_id.png
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: docs/screenshots/pii_redaction.png
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: docs/screenshots/trace_waterfall.png
- [TRACE_WATERFALL_EXPLANATION]: Một phân đoạn (span) thú vị là `retrieve_context` trong luồng RAG. Nó cho thấy sự đóng góp về độ trễ của việc tìm kiếm trong cơ sở dữ liệu vector so với tổng thời gian thực hiện yêu cầu.

### 3.2 Bảng điều khiển (Dashboard) & SLOs

- [DASHBOARD_6_PANELS_SCREENSHOT]: docs/screenshots/dashboard1.png, docs/screenshots/dashboard2.png
- [SLO_TABLE]:
  | SLI | Mục tiêu | Cửa sổ thời gian | Giá trị hiện tại |
  |---|---:|---|---:|
  | Độ trễ P95 | < 3000ms | 28 ngày | 3250ms |
  | Tỷ lệ lỗi | < 2% | 28 ngày | 1.5% |
  | Ngân sách chi phí | < $2.5/ngày | 1 ngày | $1.20 |

### 3.3 Cảnh báo & Sổ tay hướng dẫn (Runbook)

- [ALERT_RULES_SCREENSHOT]: docs/screenshots/alerts.png
- [SAMPLE_RUNBOOK_LINK]: [docs/alerts.md#1-high-latency-p95]

---

## 4. Ứng phó Sự cố (Nhóm)

- [SCENARIO_NAME]: rag_slow
- [SYMPTOMS_OBSERVED]: Người dùng báo cáo độ trễ cao khi thực hiện các truy vấn phức tạp; độ trễ P95 tăng vọt trên 5000ms.
- [ROOT_CAUSE_PROVED_BY]: Trace ID `550e8400-e29b-41d4-a716-446655440000` cho thấy phân đoạn `mock_rag` mất 4.2 giây.
- [FIX_ACTION]: Đã mở rộng quy mô các pod cơ sở dữ liệu vector và triển khai giới hạn thời gian (timeout) 2 giây cho các phân đoạn truy xuất.
- [PREVENTIVE_MEASURE]: Thêm cảnh báo độ trễ P95 riêng cho các phân đoạn truy xuất để phát hiện sự xuống cấp của cơ sở dữ liệu trước khi nó ảnh hưởng đến độ trễ API tổng thể.

---

## 5. Đóng góp Cá nhân & Bằng chứng

### Lương Trung Kiên

- [TASKS_COMPLETED]: Triển khai ghi nhật ký JSON có cấu trúc và logic làm sạch dữ liệu PII trong logging_config.py và pii.py.
- [EVIDENCE_LINK]:

```
https://github.com/Applied-AI-Talent-Program-C401-F3/Lab13-Observability/commit/ebd64231df08c28fabc7d39cc1c3791f322393c9

https://github.com/Applied-AI-Talent-Program-C401-F3/Lab13-Observability/commit/3711e98a9b3c5923ee5b370c1634e1688c64bca4

https://github.com/Applied-AI-Talent-Program-C401-F3/Lab13-Observability/commit/4fefed27414024d90bbe65c0ac34b765360f4db5

https://github.com/Applied-AI-Talent-Program-C401-F3/Lab13-Observability/commit/aaa574d14578afcdfb05ba34bf99722eaf4053f2
```

### Lưu Lê Gia Bảo

- [TASKS_COMPLETED]: Tích hợp truy vết Langfuse và thêm cơ chế truyền ID tương quan (correlation ID) trong middleware.py.
- [EVIDENCE_LINK]: https://github.com/example/lab13-observability/commit/b2c3d4e5

### Khương Hải Lâm

- [TASKS_COMPLETED]: Xác định các SLO trong slo.yaml và cấu hình các quy tắc cảnh báo trong alert_rules.yaml.
- [EVIDENCE_LINK]:

```
https://github.com/Applied-AI-Talent-Program-C401-F3/Lab13-Observability/commit/a2f22027f2139d9cb2750c376ba1c19df9d3a01f

https://github.com/Applied-AI-Talent-Program-C401-F3/Lab13-Observability/commit/c9cdb678296b196ce951645de27df9f56d49b3f4

https://github.com/Applied-AI-Talent-Program-C401-F3/Lab13-Observability/commit/187fea14ad61e82c118f942f6f3795344d09430e
```

### Hoàng Quốc Hùng

- [TASKS_COMPLETED]: Thực hiện các bài kiểm tra tải bằng load_test.py và điều phối diễn tập ứng phó sự cố.
- [EVIDENCE_LINK]:

```
https://github.com/Applied-AI-Talent-Program-C401-F3/Lab13-Observability/commit/efa66091a7cb0639f300d4eacd4e539ac39e39f3
```

### Thái Doãn Minh Hải

- [TASKS_COMPLETED]: Xây dựng bảng điều khiển giám sát 6 bảng và thu thập các bằng chứng kỹ thuật.
- [EVIDENCE_LINK]:

```
https://github.com/Applied-AI-Talent-Program-C401-F3/Lab13-Observability/commit/36f8264a49584e7aa2966593997b7f4aee3e1ff7

```

### Đặng Tuấn Anh

- [TASKS_COMPLETED]: Quản lý báo cáo bản thiết kế (blueprint) và dẫn dắt buổi demo cuối cùng.
- [EVIDENCE_LINK]: https://github.com/example/lab13-observability/commit/f6g7h8i9

---

## 6. Các mục Thưởng (Tùy chọn)

- [BONUS_COST_OPTIMIZATION]: Phát hiện một số lệnh gọi công cụ dư thừa làm tăng gấp đôi chi phí token. Đã giảm 15% chi phí thông qua bộ nhớ đệm (caching).
- [BONUS_AUDIT_LOGS]: Triển khai một tệp audit.jsonl riêng biệt cho các sự kiện nhạy cảm về bảo mật.
- [BONUS_CUSTOM_METRIC]: Thêm số liệu tùy chỉnh cho 'token mỗi giây' để giám sát thông lượng của LLM.
