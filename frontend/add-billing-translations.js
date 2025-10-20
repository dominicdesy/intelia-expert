const fs = require('fs');
const path = require('path');

// Traductions pour toutes les langues
const translations = {
  es: { // Spanish
    "billing.billingCurrency": "Moneda de facturación",
    "billing.current": "Actual",
    "billing.suggested": "Sugerida",
    "billing.notSetYet": "Aún no definida",
    "billing.currencyRequiredForUpgrade": "Debe seleccionar una moneda de facturación antes de actualizar a un plan de pago",
    "billing.changeCurrency": "Cambiar",
    "billing.selectCurrency": "Seleccione su moneda de facturación",
    "billing.loadingCurrency": "Cargando información de moneda...",
    "billing.currencyUpdated": "Moneda de facturación actualizada correctamente",
    "billing.currencyUpdateFailed": "Error al actualizar la moneda de facturación"
  },
  de: { // German
    "billing.billingCurrency": "Abrechnungswährung",
    "billing.current": "Aktuell",
    "billing.suggested": "Vorgeschlagen",
    "billing.notSetYet": "Noch nicht festgelegt",
    "billing.currencyRequiredForUpgrade": "Sie müssen eine Abrechnungswährung auswählen, bevor Sie auf einen kostenpflichtigen Plan upgraden",
    "billing.changeCurrency": "Ändern",
    "billing.selectCurrency": "Wählen Sie Ihre Abrechnungswährung",
    "billing.loadingCurrency": "Lade Währungsinformationen...",
    "billing.currencyUpdated": "Abrechnungswährung erfolgreich aktualisiert",
    "billing.currencyUpdateFailed": "Fehler beim Aktualisieren der Abrechnungswährung"
  },
  it: { // Italian
    "billing.billingCurrency": "Valuta di fatturazione",
    "billing.current": "Attuale",
    "billing.suggested": "Suggerita",
    "billing.notSetYet": "Non ancora impostata",
    "billing.currencyRequiredForUpgrade": "È necessario selezionare una valuta di fatturazione prima di passare a un piano a pagamento",
    "billing.changeCurrency": "Cambia",
    "billing.selectCurrency": "Seleziona la tua valuta di fatturazione",
    "billing.loadingCurrency": "Caricamento informazioni valuta...",
    "billing.currencyUpdated": "Valuta di fatturazione aggiornata con successo",
    "billing.currencyUpdateFailed": "Impossibile aggiornare la valuta di fatturazione"
  },
  pt: { // Portuguese
    "billing.billingCurrency": "Moeda de faturamento",
    "billing.current": "Atual",
    "billing.suggested": "Sugerida",
    "billing.notSetYet": "Ainda não definida",
    "billing.currencyRequiredForUpgrade": "Você deve selecionar uma moeda de faturamento antes de atualizar para um plano pago",
    "billing.changeCurrency": "Alterar",
    "billing.selectCurrency": "Selecione sua moeda de faturamento",
    "billing.loadingCurrency": "Carregando informações de moeda...",
    "billing.currencyUpdated": "Moeda de faturamento atualizada com sucesso",
    "billing.currencyUpdateFailed": "Falha ao atualizar a moeda de faturamento"
  },
  nl: { // Dutch
    "billing.billingCurrency": "Factureringsvaluta",
    "billing.current": "Huidige",
    "billing.suggested": "Voorgesteld",
    "billing.notSetYet": "Nog niet ingesteld",
    "billing.currencyRequiredForUpgrade": "U moet een factureringsvaluta selecteren voordat u naar een betaald abonnement kunt upgraden",
    "billing.changeCurrency": "Wijzigen",
    "billing.selectCurrency": "Selecteer uw factureringsvaluta",
    "billing.loadingCurrency": "Valuta-informatie laden...",
    "billing.currencyUpdated": "Factureringsvaluta succesvol bijgewerkt",
    "billing.currencyUpdateFailed": "Kan factureringsvaluta niet bijwerken"
  },
  pl: { // Polish
    "billing.billingCurrency": "Waluta rozliczeniowa",
    "billing.current": "Aktualna",
    "billing.suggested": "Sugerowana",
    "billing.notSetYet": "Jeszcze nie ustawiona",
    "billing.currencyRequiredForUpgrade": "Musisz wybrać walutę rozliczeniową przed przejściem na plan płatny",
    "billing.changeCurrency": "Zmień",
    "billing.selectCurrency": "Wybierz swoją walutę rozliczeniową",
    "billing.loadingCurrency": "Ładowanie informacji o walucie...",
    "billing.currencyUpdated": "Waluta rozliczeniowa została pomyślnie zaktualizowana",
    "billing.currencyUpdateFailed": "Nie udało się zaktualizować waluty rozliczeniowej"
  },
  ar: { // Arabic
    "billing.billingCurrency": "عملة الفواتير",
    "billing.current": "الحالية",
    "billing.suggested": "مقترحة",
    "billing.notSetYet": "لم يتم تعيينها بعد",
    "billing.currencyRequiredForUpgrade": "يجب عليك تحديد عملة الفواتير قبل الترقية إلى خطة مدفوعة",
    "billing.changeCurrency": "تغيير",
    "billing.selectCurrency": "حدد عملة الفواتير الخاصة بك",
    "billing.loadingCurrency": "جارٍ تحميل معلومات العملة...",
    "billing.currencyUpdated": "تم تحديث عملة الفواتير بنجاح",
    "billing.currencyUpdateFailed": "فشل تحديث عملة الفواتير"
  },
  zh: { // Chinese
    "billing.billingCurrency": "计费货币",
    "billing.current": "当前",
    "billing.suggested": "建议",
    "billing.notSetYet": "尚未设置",
    "billing.currencyRequiredForUpgrade": "在升级到付费计划之前，您必须选择计费货币",
    "billing.changeCurrency": "更改",
    "billing.selectCurrency": "选择您的计费货币",
    "billing.loadingCurrency": "正在加载货币信息...",
    "billing.currencyUpdated": "计费货币更新成功",
    "billing.currencyUpdateFailed": "计费货币更新失败"
  },
  ja: { // Japanese
    "billing.billingCurrency": "請求通貨",
    "billing.current": "現在",
    "billing.suggested": "推奨",
    "billing.notSetYet": "未設定",
    "billing.currencyRequiredForUpgrade": "有料プランにアップグレードする前に請求通貨を選択する必要があります",
    "billing.changeCurrency": "変更",
    "billing.selectCurrency": "請求通貨を選択してください",
    "billing.loadingCurrency": "通貨情報を読み込んでいます...",
    "billing.currencyUpdated": "請求通貨が正常に更新されました",
    "billing.currencyUpdateFailed": "請求通貨の更新に失敗しました"
  },
  hi: { // Hindi
    "billing.billingCurrency": "बिलिंग मुद्रा",
    "billing.current": "वर्तमान",
    "billing.suggested": "सुझाया गया",
    "billing.notSetYet": "अभी तक सेट नहीं किया गया",
    "billing.currencyRequiredForUpgrade": "भुगतान योजना में अपग्रेड करने से पहले आपको बिलिंग मुद्रा का चयन करना होगा",
    "billing.changeCurrency": "बदलें",
    "billing.selectCurrency": "अपनी बिलिंग मुद्रा चुनें",
    "billing.loadingCurrency": "मुद्रा जानकारी लोड हो रही है...",
    "billing.currencyUpdated": "बिलिंग मुद्रा सफलतापूर्वक अपडेट की गई",
    "billing.currencyUpdateFailed": "बिलिंग मुद्रा अपडेट करने में विफल"
  },
  id: { // Indonesian
    "billing.billingCurrency": "Mata uang penagihan",
    "billing.current": "Saat ini",
    "billing.suggested": "Disarankan",
    "billing.notSetYet": "Belum diatur",
    "billing.currencyRequiredForUpgrade": "Anda harus memilih mata uang penagihan sebelum meningkatkan ke paket berbayar",
    "billing.changeCurrency": "Ubah",
    "billing.selectCurrency": "Pilih mata uang penagihan Anda",
    "billing.loadingCurrency": "Memuat informasi mata uang...",
    "billing.currencyUpdated": "Mata uang penagihan berhasil diperbarui",
    "billing.currencyUpdateFailed": "Gagal memperbarui mata uang penagihan"
  },
  th: { // Thai
    "billing.billingCurrency": "สกุลเงินสำหรับการเรียกเก็บเงิน",
    "billing.current": "ปัจจุบัน",
    "billing.suggested": "แนะนำ",
    "billing.notSetYet": "ยังไม่ได้ตั้งค่า",
    "billing.currencyRequiredForUpgrade": "คุณต้องเลือกสกุลเงินสำหรับการเรียกเก็บเงินก่อนอัปเกรดเป็นแผนแบบชำระเงิน",
    "billing.changeCurrency": "เปลี่ยน",
    "billing.selectCurrency": "เลือกสกุลเงินสำหรับการเรียกเก็บเงินของคุณ",
    "billing.loadingCurrency": "กำลังโหลดข้อมูลสกุลเงิน...",
    "billing.currencyUpdated": "อัปเดตสกุลเงินสำหรับการเรียกเก็บเงินสำเร็จ",
    "billing.currencyUpdateFailed": "ไม่สามารถอัปเดตสกุลเงินสำหรับการเรียกเก็บเงิน"
  },
  tr: { // Turkish
    "billing.billingCurrency": "Faturalama para birimi",
    "billing.current": "Mevcut",
    "billing.suggested": "Önerilen",
    "billing.notSetYet": "Henüz ayarlanmadı",
    "billing.currencyRequiredForUpgrade": "Ücretli bir plana yükseltmeden önce bir faturalama para birimi seçmelisiniz",
    "billing.changeCurrency": "Değiştir",
    "billing.selectCurrency": "Faturalama para biriminizi seçin",
    "billing.loadingCurrency": "Para birimi bilgileri yükleniyor...",
    "billing.currencyUpdated": "Faturalama para birimi başarıyla güncellendi",
    "billing.currencyUpdateFailed": "Faturalama para birimi güncellenemedi"
  },
  vi: { // Vietnamese
    "billing.billingCurrency": "Tiền tệ thanh toán",
    "billing.current": "Hiện tại",
    "billing.suggested": "Được đề xuất",
    "billing.notSetYet": "Chưa được thiết lập",
    "billing.currencyRequiredForUpgrade": "Bạn phải chọn tiền tệ thanh toán trước khi nâng cấp lên gói trả phí",
    "billing.changeCurrency": "Thay đổi",
    "billing.selectCurrency": "Chọn tiền tệ thanh toán của bạn",
    "billing.loadingCurrency": "Đang tải thông tin tiền tệ...",
    "billing.currencyUpdated": "Đã cập nhật tiền tệ thanh toán thành công",
    "billing.currencyUpdateFailed": "Không thể cập nhật tiền tệ thanh toán"
  }
};

const localesDir = path.join(__dirname, 'public', 'locales');

// Function to add translations to a specific language file
function addTranslations(langCode) {
  const filePath = path.join(localesDir, `${langCode}.json`);

  try {
    // Read existing file
    const content = fs.readFileSync(filePath, 'utf8');
    const data = JSON.parse(content);

    // Add new translations
    const newTranslations = translations[langCode];
    Object.assign(data, newTranslations);

    // Write back to file with proper formatting
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n', 'utf8');

    console.log(`✓ Added translations to ${langCode}.json`);
  } catch (error) {
    console.error(`✗ Error processing ${langCode}.json:`, error.message);
  }
}

// Process all languages
const languages = Object.keys(translations);
console.log(`Adding billing translations to ${languages.length} languages...\n`);

languages.forEach(lang => {
  addTranslations(lang);
});

console.log(`\n✓ All translations added successfully!`);
