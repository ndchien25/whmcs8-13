# Review luong domain WHMCS

## Bang thong ke tong hop

| Buoc | Dieu kien chinh | Dau vet `general.log`/DB | Thanh phan tiep theo | Ket qua |
|---|---|---|---|---|
| 1. Order | Khach dat domain | `New Order Placed` trong `tblactivitylog` | Tao invoice | Order duoc ghi nhat ky |
| 2. Invoice | Order hop le | `Created Invoice` | Cho thanh toan | Invoice ton tai |
| 3. Payment | Invoice thanh toan thanh cong | `Added Invoice Payment`, `Invoice Marked Paid` | Chay xu ly domain | Bat dau xet auto-registration |
| 4. Kiem tra TLD | Co dong TLD trong `tbldomainpricing` | `SELECT autoreg FROM tbldomainpricing WHERE extension='.com'` | Chon auto/manual | Xac dinh registrar gate |
| 5. Client moi bi chan | Bat `Only Auto Provision for Existing`, client khong co Active service/domain | Activity `Automatic Domain Registration on Payment Suppressed for New Client` | Manual review/todo | Khong goi registrar |
| 6. Khong co autoreg | `tbldomainpricing.autoreg` rong | `INSERT tbltodolist` voi title `Manual Domain Registration` | Admin xu ly | Domain cho thu cong |
| 7. Auto-registration | `autoreg` hop le, khong bi suppressed | Activity `Running Automatic Domain Registration on Payment` | Chon module tu `tbldomains.registrar` | Goi `*_RegisterDomain($params)` |
| 8. Module config | Registrar da bat va co credential | `SELECT setting,value FROM tblregistrars` | Nap module | San sang goi API |
| 9. Queue check | Kiem tra job dang cho | `SELECT ... FROM tblmodulequeue` voi `module_action='RegisterDomain'` | Worker/request xu ly | Tranh chay trung job |
| 10. Thanh cong | Registrar tra ket qua thanh cong | `UPDATE tbldomains ... status='Active'` | Ghi activity/email | Domain Active |
| 11. That bai | Registrar loi/timeout/tu choi | `tblmodulelog`, `logModuleCall()` hoac error log | Retry/manual | Domain khong duoc danh dau Active |

## Ket luan da xac minh

- `tbldomainpricing.autoreg` la gate chon registrar. Khi gia tri rong, WHMCS tao todo `Manual Domain Registration` sau thanh toan.
- Khi bat `Only Auto Provision for Existing`, client moi bi chan auto-registration va ghi activity `Automatic Domain Registration on Payment Suppressed for New Client`.
- Khi du dieu kien auto, WHMCS ghi `Running Automatic Domain Registration on Payment`, gan `tbldomains.registrar`, doc `tblregistrars`, kiem tra `tblmodulequeue`, roi goi nhanh dang ky.
- Thanh cong duoc xac nhan boi `UPDATE tbldomains ... status='Active'` va activity `Domain Registered Successfully`.

## Bang chung log

### Manual

```sql
SELECT autoreg FROM tbldomainpricing WHERE extension='.com';
INSERT INTO tbltodolist (..., 'Manual Domain Registration', ...);
```

Khong duoc ket luan registrar da chay chi tu invoice Paid hoac todo.

### Suppressed cho client moi

Truoc activity suppressed, WHMCS dem dich vu/domain Active cua client. Neu khong co ban ghi Active va cau hinh **Only Auto Provision for Existing** bat, auto-registration bi bo qua. Can tim tiep `tbltodolist` hoac thao tac admin.

### Auto thanh cong (domain ID 6)

1. `UPDATE tbldomains SET registrar='registrarmodule'`.
2. Activity `Running Automatic Domain Registration on Payment`.
3. Doc cau hinh tu `tblregistrars`.
4. Kiem tra `tblmodulequeue` voi `service_type='domain'`, `service_id=6`, `module_action='RegisterDomain'`, `completed=0`.
5. Cap nhat `registrationdate`, `expirydate`, `status='Active'`.
6. Activity `Domain Registered Successfully - Domain ID: 6`.

`general.log` chi ghi SQL; muon xac nhan request/response registrar can xem `logModuleCall()`/module log. Truy van `tblmodulequeue` la buoc kiem tra job, khong tu dong chung minh job moi duoc insert.

## Cach review mot domain

1. Tim `Invoice Marked Paid` theo invoice/order.
2. Tim `SELECT autoreg` theo TLD.
3. Tim activity suppressed hoac running.
4. Kiem tra `tblmodulequeue`, `tblmodulelog` va HTTP/API log.
5. Xac nhan `tbldomains.status`, `registrar`, `registrationdate`, `expirydate`.

## Phan tich thao tac Accept Order

Trong trace `general.log` luc `15:48:03` (order `8`, domain ID `7`, `chiennd10.com`), thao tac Accept Order co chuoi:

| Thu tu | SQL/activity | Dien giai |
|---|---|---|
| 1 | Doc `tblhosting`, `tblhostingaddons`, `tbldomains` voi `orderid=8`, trang thai `Pending` | Xac dinh cac dich vu/domain cua order can accept. |
| 2 | `UPDATE tbldomains SET registrar='registrarmodule' WHERE id='7'` | Gan registrar cho domain truoc khi provision. |
| 3 | Doc `tblregistrars`, `tblorders`, `tblclients` va thong tin thanh toan | Nap context de goi module. |
| 4 | `SELECT ... FROM tblmodulequeue ... module_action='RegisterDomain' AND completed=0` | Tim job dang cho cua domain. |
| 5 | `UPDATE tblmodulequeue SET last_attempt=..., num_retries=1 ... WHERE id=2` | Worker thuc hien lan thu dau cua job queue. |
| 6 | Activity `Domain Registration Failed ... Error: Bad response received from API` | Registrar/module tra response khong hop le. |

### Ket luan cho Accept Order nay

- Accept Order da kich hoat nhánh auto-registration; khong phai chi doi thanh toan.
- Co queue `tblmodulequeue` cho `RegisterDomain`; log nay cho thay job da duoc retry (`num_retries=1`).
- Lan dang ky that bai, vi vay khong duoc coi la Accept Order thanh cong ve mat provisioning.
- Do khong co `UPDATE tbldomains ... status='Active'` hoac activity `Domain Registered Successfully` trong chuoi nay, can giu domain o trang thai chua Active va tiep tuc dieu tra `tblmodulelog`/`logModuleCall()` de tim response API.
