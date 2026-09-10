# WHMCS eNom và eNom SSL: danh sách hàm runtime

Tài liệu này ghi lại các hàm được expose khi WHMCS 8.13 load:

- `modules/registrars/enom/enom.php`: registrar domain eNom.
- `modules/servers/enomssl/enomssl.php`: server module cấp SSL eNom.

## Phạm vi và cách kiểm tra

Hai file module là ionCube protected, vì vậy danh sách dưới đây được lấy từ runtime PHP trong container WHMCS sau khi include hai module. Đây là danh sách function thực sự được đăng ký, không phải danh sách suy ra bằng cách đọc text của file encoded.

Lệnh kiểm tra:

```powershell
docker exec whmcs-813-app php -r "require '/var/www/html/init.php'; include '/var/www/html/modules/registrars/enom/enom.php'; include '/var/www/html/modules/servers/enomssl/enomssl.php'; foreach (get_defined_functions()['user'] as `$f) { if (strpos(`$f,'enom_')===0 || strpos(`$f,'enomssl_')===0) echo `$f, PHP_EOL; }"
```

Tổng cộng:

- eNom registrar: `45` hàm `enom_*`.
- eNom SSL: `13` hàm `enomssl_*`.

Tên parameter bên dưới cũng được đọc bằng `ReflectionFunction`; do module đã encode nên không có source line/documentation nội bộ.

## 1. eNom registrar

### Callback cấu hình, tra cứu và domain

| Hàm | Parameters | Vai trò |
|---|---|---|
| `enom_getconfigarray` | none | Khai báo các option cấu hình registrar: username, API token, test mode, IRTP, nameserver mặc định. |
| `enom_config_validate` | `params` | Validate cấu hình module trước khi lưu/kích hoạt. Đây là hàm validation, không phải callback lấy thông tin domain. |
| `enom_checkavailability` | `params` | Kiểm tra domain có thể đăng ký hay không. |
| `enom_getdomainsuggestions` | `params` | Lấy gợi ý domain tương tự. |
| `enom_domainsuggestionoptions` | none | Khai báo option cho chức năng domain suggestions. |
| `enom_registerdomain` | `params` | Đăng ký domain mới. |
| `enom_transferdomain` | `params` | Khởi tạo transfer domain vào eNom. |
| `enom_renewdomain` | `params` | Gia hạn domain. |
| `enom_sync` | `params` | Đồng bộ trạng thái/ngày hết hạn domain về WHMCS. |
| `enom_transfersync` | `params` | Đồng bộ trạng thái transfer đang chờ. |
| `enom_getdomaininformation` | `params` | Lấy thông tin domain và trả về `WHMCS\\Domain\\Registrar\\Domain`. API wire tương ứng của eNom là `GetDomainInfo`. |
| `enom_getpremiumprice` | `params` | Lấy giá premium domain. |
| `enom_gettldpricing` | `params` | Lấy giá theo TLD. |

### Source reference cho `enom_getconfigarray` và `enom_config_validate`

File native [modules/registrars/enom/enom.php](../modules/registrars/enom/enom.php) là ionCube protected nên không thể chỉnh sửa trực tiếp thành source PHP. Bản source clone đang phát triển nằm tại [enom-clone.php](../modules/registrars/enom/enom-clone.php); bản reference nhỏ hơn vẫn nằm tại [enom-config-reference.php](../modules/registrars/enom/enom-config-reference.php). Cả hai file này không được WHMCS tự động load và không thay thế module eNom bản quyền.

`enom_getconfigarray()` đã được đối chiếu trực tiếp với runtime WHMCS 8.13 và tạo đúng các option hiển thị trong ảnh cấu hình:

| Key | Type | Hiển thị |
|---|---|---|
| `Username` | `text` | Username |
| `Password` | `password` | API Token |
| `TestMode` | `yesno` | Enable Test Mode |
| `DisableIRTP` | `yesno` | Disable IRTP |
| `DefaultNameservers` | `yesno` | Use Default Nameservers |

`enom_config_validate(array $params)` nhận **cấu hình registrar**, không phải bộ module parameters dùng cho `RegisterDomain`, `GetDomainInformation`, `Sync`… Runtime native eNom không đọc bắt buộc `Username`/`Password`, không gọi HTTP và trả `null` cho các array rỗng, thiếu key hoặc có giá trị rỗng. Nếu truyền giá trị không phải array, PHP tự ném `TypeError` do khai báo kiểu `array`; đây không phải `InvalidConfiguration` do callback tự ném.

Kiểm tra credential/API thật sự nên nằm ở callback/API client nghiệp vụ riêng, không tự thêm vào `enom_config_validate()` nếu mục tiêu là clone đúng native behavior.

Ví dụ gọi bản reference:

```php
require_once __DIR__ . '/../modules/registrars/enom/enom-config-reference.php';

$config = enom_getconfigarray();
enom_config_validate([
    'Username' => 'test123',
    'Password' => 'api-token',
]);
```

Khác biệt quan trọng với [module parameters](https://developers.whmcs.com/domain-registrars/module-parameters/):

- Config callbacks: đọc thông tin cấu hình module (`Username`, `Password`, `TestMode`…).
- Domain callbacks: nhận dữ liệu domain/client như `sld`, `tld`, `domain`, `firstname`, `email`, `ns1`…
- Không lấy `sld`, `tld` hoặc contact fields từ `enom_config_validate()`.

### Nameserver, lock, DNS và forwarding

| Hàm | Parameters | Vai trò |
|---|---|---|
| `enom_getnameservers` | `params` | Đọc nameserver hiện tại. |
| `enom_savenameservers` | `params` | Lưu nameserver. |
| `enom_getregistrarlock` | `params` | Đọc trạng thái registrar lock. |
| `enom_saveregistrarlock` | `params` | Bật/tắt registrar lock. |
| `enom_getdns` | `params` | Đọc DNS host records. |
| `enom_savedns` | `params` | Lưu DNS host records. |
| `enom_getemailforwarding` | `params` | Đọc email forwarding. |
| `enom_saveemailforwarding` | `params` | Lưu email forwarding. |
| `enom_idprotecttoggle` | `params` | Bật/tắt ID protection/WHOIS privacy. |

### WHOIS/contact và transfer

| Hàm | Parameters | Vai trò |
|---|---|---|
| `enom_getcontactdetails` | `params` | Đọc WHOIS/contact details. |
| `enom_getregistrantcontactemailaddress` | `params` | Lấy email registrant. |
| `enom_savecontactdetails` | `params` | Lưu WHOIS/contact details. |
| `enom_normalizecontactdetails` | `params` | Chuẩn hóa dữ liệu contact trước khi gửi eNom. |
| `enom_geteppcode` | `params` | Lấy mã EPP/Auth code. |
| `enom_resendtransferapproval` | `params` | Gửi lại email phê duyệt transfer. |
| `enom_getorderid` | `params` | Lấy order ID liên quan đến domain/transfer. |
| `enom_canceldomaintransfer` | `params` | Hủy transfer domain. |
| `enom_resendirtpverificationemail` | `params` | Gửi lại email xác minh IRTP. |

### Private nameserver và nút admin

| Hàm | Parameters | Vai trò |
|---|---|---|
| `enom_registernameserver` | `params` | Đăng ký glue/private nameserver. |
| `enom_modifynameserver` | `params` | Sửa glue/private nameserver. |
| `enom_deletenameserver` | `params` | Xóa glue/private nameserver. |
| `enom_admincustombuttonarray` | `params` | Khai báo các nút custom ở admin. |

### Helper nội bộ và extension/TLD

| Hàm | Parameters | Vai trò |
|---|---|---|
| `enom_normalise_status` | `status` | Chuẩn hóa status từ eNom. Tên dùng British spelling là `normalise`; `enom_normalize_status` không được expose trong runtime. |
| `enom_set_initial_contact_data` | `Enom`, `params` | Chuẩn bị dữ liệu contact ban đầu. |
| `enom_populate_additional_fields` | `Enom`, `params` | Bổ sung field phụ cho request/domain. |
| `enom_getaueligibilityattributes` | `params` | Lấy thuộc tính eligibility của TLD `.au` hoặc extension liên quan. |
| `enom_getextattributes` | `params`, `tld` | Lấy extended attributes theo TLD. |
| `enom_getciraagreementversion` | `params` | Lấy phiên bản thỏa thuận CIRA. |
| `enom__isidn` | `params` | Kiểm tra domain IDN. Dấu gạch dưới kép là tên helper nội bộ. |
| `enom__getasciivalue` | `params`, `uniCodeValue` | Chuyển/tra giá trị ASCII của domain IDN. |
| `enom__replaceasciivalue` | `params`, `dataString`, `uniCodeKey` | Thay giá trị Unicode/ASCII trong dữ liệu request. |
| `enom__preparenameserversforsave` | `params` | Chuẩn bị nameserver trước khi lưu. |

## 1.1. Mapping `GetDomainInfo` -> `WHMCS\\Domain\\Registrar\\Domain`

`enom_getdomaininformation($params)` là callback cấp domain-information của registrar. Lệnh wire mà eNom nhận là `GetDomainInfo`. Callback này không trả nguyên response XML của eNom; module chọn một số field rồi đưa vào object `WHMCS\\Domain\\Registrar\\Domain`.

### Các thuộc tính có trong object WHMCS

Các setter/getter dưới đây được xác nhận từ class runtime WHMCS 8.13:

```text
setRegistrantEmailAddress() / getRegistrantEmailAddress()
setDomain() / getDomain()
setExpiryDate() / getExpiryDate()
setRegistrationStatus() / getRegistrationStatus()
setRestorable() / getRestorable()
setRenewBeforeExpiration() / getRenewBeforeExpiration()
setIdProtectionStatus() / getIdProtectionStatus()
setDnsManagementStatus() / getDnsManagementStatus()
setEmailForwardingStatus() / getEmailForwardingStatus()
setNameservers() / getNameservers()
setTransferLock() / getTransferLock()
setTransferLockExpiryDate() / getTransferLockExpiryDate()
setIrtpOptOutStatus() / getIrtpOptOutStatus()
setIrtpTransferLock() / getIrtpTransferLock()
setIrtpTransferLockExpiryDate() / getIrtpTransferLockExpiryDate()
setDomainContactChangePending() / isContactChangePending()
setDomainContactChangeExpiryDate() / getDomainContactChangeExpiryDate()
setPendingSuspension() / getPendingSuspension()
setIsIrtpEnabled() / getIsIrtpEnabled()
setIrtpVerificationTriggerFields() / getIrtpVerificationTriggerFields()
```

### Bảng mapping

| Field trong eNom `GetDomainInfo` | Setter/thuộc tính WHMCS tương ứng | Mức độ | Ghi chú |
|---|---|---|---|
| `GetDomainInfo.domainname` | `setDomain()` | Contract + response | Ví dụ fixture hiện tại: `chiennd1.com`. |
| `GetDomainInfo.status.expiration` | `setExpiryDate()` | Contract + response | eNom trả định dạng kiểu `4/1/2027 7:34:00 PM`; WHMCS chuẩn hóa thành date object/giá trị ngày hết hạn của Domain. |
| `GetDomainInfo.status.registrationstatus` | `setRegistrationStatus()` | Contract + helper runtime | Module có helper `enom_normalise_status($status)`, nên không nên giả định status eNom được giữ nguyên 100%. |
| `GetDomainInfo.status.restorable` | `setRestorable()` | Contract-compatible | `True`/`False` cho biết domain có thể restore hay không. Cần kiểm thử thêm từng status nếu cần khẳng định exact mapping của native encoded module. |
| `GetDomainInfo.status.renewbeforeexpiration` | `setRenewBeforeExpiration()` | Contract-compatible | Field trong fixture đang rỗng. |
| `GetDomainInfo.services.entry[name=dnsserver].configuration.dns[]` | `setNameservers()` | Response + contract | Fixture có `dns1.name-services.com` đến `dns5.name-services.com`. |
| `GetDomainInfo.services.entry[name=wpps]` | `setIdProtectionStatus()` | Inferred from service name | `wpps` là WHOIS privacy/ID protection service. Native module cũng có callback riêng `enom_idprotecttoggle()`. |
| `GetDomainInfo.services.entry[name=whoispublicity].whoispublicity.enabled` | `setIdProtectionStatus()` | Possible/conditional | Có thể là nguồn trạng thái publicity/privacy theo TLD; không gộp chắc chắn với `wpps` nếu chưa test response biến thể. |
| `GetDomainInfo.services.entry[name=dnssettings]` | `setDnsManagementStatus()` | Possible/conditional | Đây là DNS hosting/settings service; DNS records chi tiết không nằm trong Domain object. Callback quản lý records riêng là `enom_getdns()`/`enom_savedns()`. |
| `GetDomainInfo.services.entry[name=emailset]` hoặc plain field `EmailForwarding` | `setEmailForwardingStatus()` | Possible/conditional | Email forwarding có callback riêng `enom_getemailforwarding()`/`enom_saveemailforwarding()`. |
| `GetDomainInfo.services.entry[name=irtpsettings].irtpsetting.optout` | `setIrtpOptOutStatus()` | Response + contract | Fixture: `False`. |
| `GetDomainInfo.services.entry[name=irtpsettings].irtpsetting.transferlock` | `setIrtpTransferLock()` | Response + contract | Fixture: `True`. Đây là IRTP lock; không nên đồng nhất với registrar lock thường. |
| `GetDomainInfo.services.entry[name=irtpsettings].irtpsetting.transferlockexpdate` | `setIrtpTransferLockExpiryDate()` | Response + contract, runtime cần kiểm tra | XML có text date và các thuộc tính `utc`, `epoch`, `daysremaining`; native eNom callback trong fixture hiện tại vẫn cho getter `NULL`, nên không khẳng định module đang map field này. |
| `GetDomainInfo.services.entry[name=raasettings].raasetting.domainsuspended` | `setPendingSuspension()` nếu callback trả object | Domain contract | Về mặt object contract: `1` => pending suspension `true`, `0` => `false`. Nhưng với nhánh RAA bị chặn, callback có thể ném exception trước khi `Domain` được trả về; khi đó Smarty nhận `domainInformation = null`. |
| `GetDomainInfo.services.entry[name=raasettings].raasetting.verificationstatus` | Không map trực tiếp vào setter chuẩn của `Domain` | Runtime behavior | Metadata/trạng thái RAA contact verification, ví dụ `Verified`, `Active`, `Suspended`. Dùng để hiểu lý do suspend hoặc nhánh lỗi, nhưng không phải field boolean chính của `setPendingSuspension()`. |
| Contact email/WHOIS fields | `setRegistrantEmailAddress()` và contact state | Separate callback | `GetDomainInfo` fixture không có đầy đủ contact. Dữ liệu contact lấy qua `enom_getcontactdetails()`/`enom_getregistrantcontactemailaddress()`. |
| `status.deletebydate`, `deletetype`, `registrar`, `purchase-status`, `belongs-to`, `partyid` | Không có setter chuẩn trong Domain | Ignored/other logic | Không phải thuộc tính chuẩn của `WHMCS\\Domain\\Registrar\\Domain`. |
| `domainnameid` | Không có setter chuẩn trong Domain | Ignored/other logic | ID nội bộ eNom; không phải WHMCS domain ID. |
| `services.dnssettings.configuration.host[]` | Không có setter trong Domain | Separate DNS data | Đây là host records (`A`, `MX`...), thuộc API DNS riêng. |
| `ParkingEnabled`, `website`, `phone`, `map`, `mobilizer`, `EmailAutoRenew`, `URLForwarding`, `URLForwardExpDate`, pricing fields | Không có setter chuẩn trong Domain | Ignored/other callback | Một số dịch vụ có callback riêng; URL forwarding không có property tương ứng trong class Domain này. |

### Mapping riêng cho `status.registrationstatus`

`registrationstatus` trong response eNom không được giữ nguyên 1-1 khi đi vào `WHMCS\Domain\Registrar\Domain::registrationStatus`. Native module gọi helper runtime `enom_normalise_status($status)` trước khi set vào Domain object.

Kết quả test trực tiếp trong container WHMCS 8.13 với helper native:

```powershell
docker exec whmcs-813-app php -r "require '/var/www/html/init.php'; include '/var/www/html/includes/registrarfunctions.php'; include '/var/www/html/modules/registrars/enom/enom.php'; foreach (['Registered','Expired','PendingDelete'] as `$s) { echo `$s,' => '; var_export(enom_normalise_status(`$s)); echo PHP_EOL; }"
```

| Raw `GetDomainInfo.status.registrationstatus` từ eNom/mock | `enom_normalise_status()` | `Domain::getRegistrationStatus()` kỳ vọng | Bằng chứng | Ghi chú |
|---|---|---|---|---|
| `Expired` | `Expired` | `Expired` | Runtime confirmed | Phải đúng literal `Expired`: đúng chữ hoa/thường, không dư khoảng trắng. Đây là case duy nhất đã xác nhận làm object không còn `Active`. |
| `Registered` | `Active` | `Active` | Runtime confirmed | Đây là trạng thái healthy thường gặp của eNom. |
| `registred` | `Active` | `Active` | Runtime confirmed | Module có vẻ chấp nhận cả lỗi chính tả cũ/biến thể nội bộ bằng cách fallback Active. |
| `Active` | `Active` | `Active` | Runtime confirmed | Nếu raw đã là Active thì giữ Active. |
| `PendingDelete` | `Active` | `Active` | Runtime confirmed | Đây là lý do fixture đang để `PendingDelete` nhưng var_dump vẫn thấy `registrationStatus = Active`. |
| `Extended RGP` | `Active` | `Active` | Runtime confirmed | Không được module map thành Expired/Redemption. |
| `Redemption Period` | `Active` | `Active` | Runtime confirmed | Không được module map thành Expired/Redemption. |
| `Pending` | `Active` | `Active` | Runtime confirmed | Fallback Active. |
| `TransferPending` | `Active` | `Active` | Runtime confirmed | Fallback Active. |
| `Cancelled` | `Active` | `Active` | Runtime confirmed | Fallback Active. |
| `Suspended` | `Active` | `Active` | Runtime confirmed | Raw registration status này không tự tạo lỗi suspend; lỗi suspend đã xác nhận nằm ở `raasettings.verificationstatus=Suspended` + `domainsuspended=1`. |
| `Unknown` hoặc chuỗi rỗng | `Active` | `Active` | Runtime confirmed | Fallback Active. |
| `expired`, `EXPIRED`, ` Expired `, `Expired `, `Registration Expired` | `Active` | `Active` | Runtime confirmed | Helper so khớp case-sensitive/trim-sensitive; mock muốn expired phải dùng đúng `Expired`. |

Kết luận để sửa mock: nếu mục tiêu là xác nhận `Domain::$registrationStatus` đổi sang expired, sửa XML/TXT response thành:

```xml
<registrationstatus>Expired</registrationstatus>
```

Không dùng `PendingDelete` cho test này, vì trong WHMCS eNom native callback `PendingDelete` đang normalize thành `Active`.

Lưu ý thêm: eNom documentation hiện tại chỉ mô tả `GetDomainInfo` có output field `RegistrationStatus`, nhưng không liệt kê enum đầy đủ cho riêng field này. Các bài support của eNom/ICANN có các lifecycle/status code như `ok`, `clientHold`, `pendingDelete`, `pendingTransfer`, `redemptionPeriod`, `serverHold`..., nhưng đó là domain/WHOIS lifecycle status, không đồng nghĩa với việc WHMCS eNom module sẽ map chúng vào `Domain::registrationStatus`.

## 1.2. Spec lỗi xác minh contact từ `GetDomainInfo`

### Text hiển thị/exception đã xác nhận

Khi callback native `enom_GetDomainInformation($params)` nhận trạng thái RAA dưới đây, runtime phát sinh exception:

```text
WHMCS\Exception\Module\NotServicable
This domain has been suspended by the registrar for failing to verify the contact email address.
```

Chuỗi tiếng Anh ở trên là `getMessage()` của exception do module eNom native ném ra. Nó không nằm trong source `enom.php` dạng text vì file module được bảo vệ bằng ionCube.

Trong trang admin, WHMCS bắt exception và dùng hai phần riêng:

| Thành phần | Giá trị | Nguồn |
|---|---|---|
| Tiêu đề alert | `Registrar Error` | `admin/lang/english.php`, key `$_ADMINLANG['domains']['registrarerror']` |
| Nội dung alert | `This domain has been suspended by the registrar for failing to verify the contact email address.` | `$exception->getMessage()` từ callback eNom |

### Điều kiện trạng thái gây lỗi

| Field eNom | Trạng thái gây lỗi | Ý nghĩa |
|---|---:|---|
| `GetDomainInfo.services.entry[name=raasettings].raasetting.domainsuspended` | `1` | Cờ suspend từ eNom. Nếu callback tiếp tục trả object thì đây là giá trị để map `setPendingSuspension(true)`; trong nhánh bị chặn, object không được trả về. |
| `GetDomainInfo.services.entry[name=raasettings].raasetting.verificationstatus` | `Suspended` hoặc giá trị mô tả khác | Metadata/lý do contact verification. Runtime test với cả `Suspended` và `Verified` đều cho thấy `domainsuspended=1` vẫn làm native callback ném exception; field này không phải điều kiện cần để exception xảy ra. |
| `status.registrationstatus` | Có thể vẫn là `Registered` | Không đủ để kết luận domain healthy; phải kiểm tra thêm `raasettings` |

Về riêng phép map vào `Domain`, có thể biểu diễn bằng logic tương đương:

```php
$willDomainSuspend = ((string) $raasetting->domainsuspended === '1');
$domain->setPendingSuspension($willDomainSuspend);
```

Do đó, nếu callback đi tới bước khởi tạo object, `domainsuspended` là input boolean chính; không cần dùng `verificationstatus` để tính boolean này. Nhưng callback native eNom có thể kiểm tra RAA và ném exception trước khi trả object, nên `domainsuspended=1` không đảm bảo lúc nào cũng nhận được một `Domain` object để dump.

Response fixture gây lỗi trước đây:

```xml
<entry name="raasettings">
  <raasetting>
    <verificationstatus><![CDATA[Suspended]]></verificationstatus>
    <domainsuspended><![CDATA[1]]></domainsuspended>
  </raasetting>
</entry>
```

Runtime test trực tiếp với fixture hiện tại:

```text
callback: enom_GetDomainInformation($params)
domainsuspended: 1
verificationstatus: Suspended (Verified cũng cho cùng kết quả)
result: WHMCS\\Exception\\Module\\NotServicable
message: This domain has been suspended by the registrar for failing to verify the contact email address.
Smarty: $domainInformation === null
```

Lệnh Reflection dùng để kiểm tra callback (fixture phải có `domainsuspended=1`):

```powershell
docker exec whmcs-813-app php -r "require '/var/www/html/init.php'; include '/var/www/html/includes/registrarfunctions.php'; include '/var/www/html/modules/registrars/enom/enom.php'; `$r=new ReflectionFunction('enom_getdomaininformation'); `$params=['domain'=>'chiennd1.com','sld'=>'chiennd1','tld'=>'com','username'=>'enomtest_reseller','password'=>'test','testmode'=>true,'configoption1'=>'enomtest_reseller','configoption2'=>'test','registrar'=>'enom','userid'=>1]; try { `$v=`$r->invoke(`$params); var_dump(`$v); } catch (Throwable `$e) { echo get_class(`$e), PHP_EOL, `$e->getMessage(), PHP_EOL; }"
```

Kết quả thực tế với fixture hiện tại:

```text
THROWN=WHMCS\\Exception\\Module\\NotServicable
MESSAGE=This domain has been suspended by the registrar for failing to verify the contact email address.
CODE=0
```

Vì exception xảy ra trước `return Domain`, Smarty không thể dump được `getPendingSuspension()`. Do đó không nên kết luận `setPendingSuspension()` đã nhận `true` từ kết quả `$domainInformation`; trong request này setter có thể chưa bao giờ được quan sát từ phía template.

### Phân biệt fixture healthy và fixture lỗi

Fixture hiện tại trong workspace đang dùng để tái hiện nhánh lỗi contact suspension:

```xml
<domainname sld="chiennd1" tld="com" domainnameid="152809550">chiennd1.com</domainname>
<status>
  <registrationstatus>PendingDelete</registrationstatus>
</status>
<entry name="raasettings">
  <raasetting>
    <verificationstatus><![CDATA[Suspended]]></verificationstatus>
    <domainsuspended><![CDATA[1]]></domainsuspended>
  </raasetting>
</entry>
```

Vì vậy fixture này không phù hợp để smoke-test object `Domain` healthy: native callback có thể ném exception RAA trước khi trả object. Muốn test riêng mapping status/object, dùng biến thể healthy sau:

```xml
<status>
  <registrationstatus>Expired</registrationstatus>
</status>
<entry name="raasettings">
  <raasetting>
    <verificationstatus><![CDATA[Verified]]></verificationstatus>
    <domainsuspended><![CDATA[0]]></domainsuspended>
  </raasetting>
</entry>
```

Nếu muốn test domain đang hoạt động, thay `Expired` bằng `Registered`; kết quả WHMCS vẫn là `Active` do `enom_normalise_status()`.

### Lưu ý khi tạo fixture

- Request thực tế trong log là `sld=chiennd1&tld=com`, vì vậy response phải trả `chiennd1.com`; response cũ trả `chiennd.net` là không nhất quán.
- `GetContacts` cũng phải dùng cùng domain/domain ID với `GetDomainInfo` trong fixture test để tránh trộn dữ liệu contact của domain khác.
- Không dùng `Suspended`/`domainsuspended=1` trong fixture mặc định nếu mục tiêu là kiểm tra mapping object `Domain`; hãy dùng một fixture lỗi riêng để kiểm tra nhánh exception.

### Phân biệt `irtpVerificationTriggerFields` và `$irtpFields`

Runtime test với `GetDomainInfo` fixture hiện tại cho object:

```text
getIrtpOptOutStatus()              => false
getIrtpTransferLock()              => true
getIrtpTransferLockExpiryDate()    => NULL
getPendingSuspension()             => false
getIsIrtpEnabled()                 => false
getIrtpVerificationTriggerFields() => [
    'Registrant' => [
        'First Name',
        'Last Name',
        'Organisation Name',
        'Email',
    ],
]
```

Do đó, `irtpVerificationTriggerFields` không được lấy từ XML block `services.entry[name=irtpsettings]`. Block đó chỉ cung cấp trạng thái IRTP (`optout`, `transferlock`, `transferlockexpdate`). Danh sách field trigger là metadata riêng do module/core đặt vào `Domain` object.

Trong template, `$irtpFields` là Smarty variable được core chuẩn bị riêng để đánh dấu input bằng CSS class `irtp-field`. Không nên giả định `$irtpFields` luôn là kết quả trực tiếp của:

```php
$domainInformation->getIrtpVerificationTriggerFields()
```

Nếu object có `irtpVerificationTriggerFields` nhưng `$irtpFields` dump ra `array(0)`, cần kiểm tra thêm điều kiện core dùng khi assign Smarty variable, đặc biệt `getIsIrtpEnabled()`. Với fixture/runtime hiện tại, getter này trả `false`, nên `$irtpFields` rỗng là hành vi có thể xảy ra dù danh sách trigger vẫn tồn tại trong object.

### Cần phân biệt với `Sync`

`enom_sync($params)` không dùng object `Domain` theo contract thông thường. Nó trả về array đồng bộ, ví dụ:

```php
[
    'expirydate' => 'YYYY-MM-DD',
    'active' => true,
    'transferredAway' => false,
]
```

Vì vậy các key `expirydate`, `active`, `transferredAway` của `Sync` không phải tên property được thêm tùy ý vào object `Domain`.

### Cách dump object trong template

Để xem object mà WHMCS truyền vào Smarty, có thể tạm dùng:

```smarty
{if $domainInformation}
    <pre style="white-space: pre-wrap; text-align: left;">{$domainInformation|@var_dump}</pre>
{/if}
```

Hoặc log an toàn hơn ở PHP bằng cách chỉ đọc các getter, tránh dump toàn bộ contact data:

```php
logActivity(json_encode([
    'class' => get_class($domainInformation),
    'domain' => $domainInformation->getDomain(),
    'expiryDate' => (string) $domainInformation->getExpiryDate(),
    'registrationStatus' => $domainInformation->getRegistrationStatus(),
    'nameservers' => $domainInformation->getNameservers(),
    'transferLock' => $domainInformation->getTransferLock(),
    'irtpTransferLock' => $domainInformation->getIrtpTransferLock(),
], JSON_UNESCAPED_SLASHES));
```

Không nên ghi raw response eNom, API token hoặc toàn bộ contact object vào log production.

## 2. eNom SSL server module

Module này nằm ở `modules/servers/enomssl`, không phải registrar module. Prefix callback là `enomssl_`.

| Hàm | Parameters | Vai trò |
|---|---|---|
| `enomssl_metadata` | none | Metadata của server module. |
| `enomssl_configoptions` | `params` | Khai báo/cung cấp option cấu hình server module. |
| `enomssl_createaccount` | `params` | Tạo account/provisioning account SSL. |
| `enomssl_terminateaccount` | `params` | Terminate account/dịch vụ SSL. |
| `enomssl_admincustombuttonarray` | none | Khai báo custom buttons trong admin. |
| `enomssl_resend` | `params` | Gửi lại thông tin/chứng thư hoặc thao tác resend của SSL order. |
| `enomssl_clientarea` | `params` | Chuẩn bị dữ liệu hiển thị ở client area. |
| `enomssl_adminservicestabfields` | `params` | Khai báo field hiển thị trong tab Services ở admin. |
| `enomssl_sslstepone` | `params` | Xử lý bước 1 của quy trình SSL. |
| `enomssl_sslsteptwo` | `params` | Xử lý bước 2 của quy trình SSL. |
| `enomssl_sslstepthree` | `params` | Xử lý bước 3 của quy trình SSL. |
| `enomssl_call` | `fields`, `testmode` | Helper gọi API eNom SSL. |
| `enomssl_customactions` | `params` | Khai báo/xử lý custom actions của SSL service. |

## 3. Phân biệt callback và helper

WHMCS sẽ gọi các callback theo convention của module. Ví dụ:

```text
enom_GetDomainInformation($params)
enom_GetNameservers($params)
enom_Sync($params)
enomssl_CreateAccount($params)
enomssl_ClientArea($params)
```

PHP không phân biệt hoa thường ở tên function, nên runtime hiển thị lowercase (`enom_getdomaininformation`) nhưng callback thường được viết trong tài liệu WHMCS với chữ hoa theo tên chức năng.

Các hàm có hai dấu gạch dưới sau prefix, ví dụ `enom__isidn`, là helper nội bộ và không phải callback registrar công khai của WHMCS.

## 4. Giới hạn của tài liệu

- Danh sách và signatures là bằng chứng runtime trên bản WHMCS `8.13.5`, BuildId `88ca2f8487.1153` trong workspace này.
- Vì code được bảo vệ bằng ionCube, tài liệu không khẳng định implementation chi tiết bên trong từng hàm.
- Mô tả vai trò dựa trên tên callback WHMCS, metadata module, API traffic hiện có và hành vi runtime; những hàm helper nội bộ cần kiểm thử thêm nếu cần biết mapping chính xác.
- Không ghi secret API, token, contact data hoặc toàn bộ response eNom vào tài liệu.

## 5. Tài liệu liên quan

- [WHMCS Registrar Function Index](https://developers.whmcs.com/domain-registrars/function-index)
- [WHMCS Domain Information](https://developers.whmcs.com/domain-registrars/domain-information)
- [eNom GetDomainInfo API](https://api.enom.com/docs/getdomaininfo)
- [eNom SSL module documentation](https://go.whmcs.com/1889/enom-ssl)
