import { type ReactNode, useEffect, useRef, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import NotFound from '@/pages/not-found';
import { Route, Switch, useLocation, Router as WouterRouter } from 'wouter';
import { Activity, ArrowDownToLine, ArrowRight, CalendarDays, Check, CheckCircle2, CircleHelp, ClipboardList, Download, FileText, Heart, ImagePlus, Info, LockKeyhole, Menu, Printer, RotateCcw, ShieldCheck, Upload, X } from 'lucide-react';

type Answer = 'yes' | 'no' | 'unknown' | '';
type Intake = {
  initials: string; age: string; gender: string; fitzpatrick: string; region: string; diameter: string;
  smoking: Answer; alcohol: Answer; pesticide: Answer; personalCancer: Answer; familyCancer: Answer;
  itch: Answer; growth: Answer; pain: Answer; change: Answer; bleeding: Answer; elevation: Answer;
};
type UploadedImage = { fileName: string; mime: string; width: number; height: number; previewUrl: string; flags: { resolution: 'good'|'low'; brightness: 'good'|'dim'|'bright'|'check'; blur: 'good'|'check' } };
type RoutineItem = { id: string; time: string; title: string; guidance: string; ruleId: string; checked: boolean };
type PlannerSettings = { routine: RoutineItem[]; wakeTime: string; sleepTime: string };

const queryClient = new QueryClient();
const blankIntake: Intake = { initials:'', age:'', gender:'', fitzpatrick:'', region:'', diameter:'', smoking:'', alcohol:'', pesticide:'', personalCancer:'', familyCancer:'', itch:'', growth:'', pain:'', change:'', bleeding:'', elevation:'' };
const starterRoutine: RoutineItem[] = [
  { id:'am-shade', time:'MORNING', title:'Make shade part of the plan', guidance:'Choose shade when practical, especially around midday. A hat and protective clothing are useful everyday options.', ruleId:'UV-01', checked:false },
  { id:'am-sunscreen', time:'BEFORE GOING OUT', title:'Use broad-spectrum sun protection', guidance:'Apply broad-spectrum SPF 30+ sunscreen to exposed skin and follow the label directions.', ruleId:'UV-02', checked:false },
  { id:'outdoor-reapply', time:'WHILE OUTDOORS', title:'Check sun-protection timing', guidance:'When outdoors, follow the sunscreen label and reapply at least every two hours, and after swimming or sweating.', ruleId:'UV-03', checked:false },
  { id:'hydration-break', time:'AFTERNOON', title:'Take a hydration break', guidance:'Pause for water if it fits your usual routine and personal needs.', ruleId:'WELL-01', checked:false },
  { id:'pm-skin', time:'EVENING', title:'Notice what is changing', guidance:'If you notice a new or changing spot, note when you first saw it and consider arranging a visit with a qualified clinician.', ruleId:'SKIN-01', checked:false },
  { id:'sleep-routine', time:'BEFORE BED', title:'Make space for rest', guidance:'Follow a sleep routine that works for you.', ruleId:'WELL-02', checked:false },
  { id:'wellbeing-nudge', time:'ANYTIME', title:'Consider a healthy change', guidance:'If smoking or alcohol is a concern for you, a clinician can discuss support options without judgment.', ruleId:'WELL-03', checked:false },
  { id:'weekly-check', time:'ONCE THIS WEEK', title:'Set aside a few minutes for a skin check', guidance:'In good light, note any changes you want to discuss with a clinician. A photo may help you keep track; it does not diagnose a spot.', ruleId:'SKIN-02', checked:false },
  { id:'clinician-visit', time:'IF A SPOT CONCERNS YOU', title:'Consider a clinician visit', guidance:'If a spot is changing, bleeding, painful, or concerning to you, seek advice from a qualified clinician.', ruleId:'CARE-03', checked:false },
];

function loadPlannerSettings(): PlannerSettings {
  let savedItems: unknown[] = [];
  let wakeTime = '07:00';
  let sleepTime = '22:00';
  try {
    const current = JSON.parse(localStorage.getItem('dermasense-planner-v2') || 'null');
    if (current && typeof current === 'object') {
      savedItems = Array.isArray(current.routine) ? current.routine : [];
      if (typeof current.wakeTime === 'string' && /^\d{2}:\d{2}$/.test(current.wakeTime)) wakeTime = current.wakeTime;
      if (typeof current.sleepTime === 'string' && /^\d{2}:\d{2}$/.test(current.sleepTime)) sleepTime = current.sleepTime;
    } else {
      const legacy = JSON.parse(localStorage.getItem('dermasense-routine-v1') || '[]');
      savedItems = Array.isArray(legacy) ? legacy : [];
    }
  } catch {
    savedItems = [];
  }
  const checkedById = new Map<string, boolean>();
  savedItems.forEach(item => {
    if (item && typeof item === 'object' && 'id' in item && 'checked' in item
      && typeof item.id === 'string' && typeof item.checked === 'boolean') {
      checkedById.set(item.id, item.checked);
    }
  });
  return {
    routine: starterRoutine.map(item => ({ ...item, checked: checkedById.get(item.id) ?? false })),
    wakeTime,
    sleepTime,
  };
}

function App() {
  const [intake, setIntake] = useState<Intake>(blankIntake);
  const [image, setImage] = useState<UploadedImage|null>(null);
  const [consent, setConsent] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<{age?: string; diameter?: string}>({});
  const [reportError, setReportError] = useState('');
  const [isSavingPdf, setIsSavingPdf] = useState(false);
  const [savedPlanner] = useState(loadPlannerSettings);
  const [routine, setRoutine] = useState<RoutineItem[]>(savedPlanner.routine);
  const [wakeTime, setWakeTime] = useState(savedPlanner.wakeTime);
  const [sleepTime, setSleepTime] = useState(savedPlanner.sleepTime);
  const [storageWarning, setStorageWarning] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  useEffect(() => {
    try {
      localStorage.setItem('dermasense-planner-v2', JSON.stringify({ routine, wakeTime, sleepTime }));
      setStorageWarning('');
    } catch {
      setStorageWarning('Browser storage is unavailable. Routine check-offs and schedule times may reset when this page closes.');
    }
  }, [routine, wakeTime, sleepTime]);
  useEffect(() => () => { if (image?.previewUrl) URL.revokeObjectURL(image.previewUrl); }, [image?.previewUrl]);

  const change = (key: keyof Intake, value: string) => {
    if (key === 'age') {
      const age = value === '' ? undefined : Number(value);
      const message = age !== undefined && (!Number.isInteger(age) || age < 0 || age > 120)
        ? 'Enter a whole number from 0 to 120.'
        : undefined;
      setFieldErrors(current => ({ ...current, age: message }));
    }
    if (key === 'diameter') {
      const diameter = value === '' ? undefined : Number(value);
      const message = diameter !== undefined && (!Number.isFinite(diameter) || diameter < 0 || diameter > 200)
        ? 'Enter a diameter from 0 to 200 mm.'
        : undefined;
      setFieldErrors(current => ({ ...current, diameter: message }));
    }
    setReportError('');
    setIntake(current => ({ ...current, [key]: value }));
  };
  const upload = async (file?: File) => {
    setUploadError('');
    if (!file) return;
    if (!['image/jpeg','image/png'].includes(file.type)) { setUploadError('Please choose a JPG or PNG image.'); return; }
    if (file.size > 20 * 1024 * 1024) { setUploadError('Please choose an image smaller than 20 MB.'); return; }
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      const scale = Math.min(1, 320 / Math.max(img.naturalWidth, img.naturalHeight));
      canvas.width = Math.max(1, Math.round(img.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(img.naturalHeight * scale));
      if (ctx) {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
        const luminance = new Float32Array(canvas.width * canvas.height);
        let total = 0;
        for (let i = 0; i < data.length; i += 4) {
          const pixel = i / 4;
          const lum = .2126 * data[i] + .7152 * data[i+1] + .0722 * data[i+2];
          luminance[pixel] = lum;
          total += lum;
        }
        let laplacianSum = 0, laplacianSquared = 0, laplacianCount = 0;
        for (let y = 1; y < canvas.height - 1; y++) {
          for (let x = 1; x < canvas.width - 1; x++) {
            const index = y * canvas.width + x;
            const laplacian = luminance[index - canvas.width] + luminance[index + canvas.width]
              + luminance[index - 1] + luminance[index + 1] - 4 * luminance[index];
            laplacianSum += laplacian;
            laplacianSquared += laplacian * laplacian;
            laplacianCount++;
          }
        }
        const avg = total / (data.length / 4);
        const laplacianMean = laplacianCount ? laplacianSum / laplacianCount : 0;
        const laplacianVariance = laplacianCount ? laplacianSquared / laplacianCount - laplacianMean * laplacianMean : 0;
        setImage({ fileName:file.name, mime:file.type, width:img.naturalWidth, height:img.naturalHeight, previewUrl:url,
          flags:{ resolution:img.naturalWidth >= 800 && img.naturalHeight >= 800 ? 'good':'low', brightness:avg < 40 ? 'dim':avg > 220 ? 'bright':'good', blur:laplacianVariance < 10 ? 'check':'good' } });
      } else {
        setImage({ fileName:file.name, mime:file.type, width:img.naturalWidth, height:img.naturalHeight, previewUrl:url, flags:{ resolution:img.naturalWidth >= 800 && img.naturalHeight >= 800 ? 'good':'low', brightness:'check', blur:'check' } });
      }
    };
    img.onerror = () => { URL.revokeObjectURL(url); setUploadError('This image could not be opened. Please try another JPG or PNG.'); };
    img.src = url;
  };
  const clearImage = () => { if (image) URL.revokeObjectURL(image.previewUrl); setImage(null); if (inputRef.current) inputRef.current.value = ''; };
  const toggleRoutine = (id:string) => setRoutine(items => items.map(item => item.id === id ? { ...item, checked:!item.checked } : item));
  const scheduledTime = (id: string) => {
    const [wakeHour, wakeMinute] = wakeTime.split(':').map(Number);
    const [sleepHour, sleepMinute] = sleepTime.split(':').map(Number);
    const wake = wakeHour * 60 + wakeMinute;
    let sleep = sleepHour * 60 + sleepMinute;
    if (sleep <= wake) sleep += 24 * 60;
    const offsets: Record<string, number> = {
      'am-shade': 15, 'am-sunscreen': 30, 'outdoor-reapply': 150,
      'hydration-break': 360, 'pm-skin': -120, 'sleep-routine': -45,
      'wellbeing-nudge': 300, 'weekly-check': 45, 'clinician-visit': 60,
    };
    const offset = offsets[id] ?? 30;
    const total = id === 'pm-skin' || id === 'sleep-routine'
      ? sleep + offset
      : wake + offset;
    const normalized = ((total % 1440) + 1440) % 1440;
    return `${String(Math.floor(normalized / 60)).padStart(2, '0')}:${String(normalized % 60).padStart(2, '0')}`;
  };
  const addCalendar = () => {
    const lines = ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//DermaSense AI//Safe Corner//EN'];
    routine.forEach((item, index) => {
      const date = new Date(); date.setDate(date.getDate() + 1); date.setHours(0, 0, 0, 0);
      const [hour, minute] = scheduledTime(item.id).split(':').map(Number);
      date.setHours(hour, minute, 0, 0);
      const end = new Date(date.getTime() + 15 * 60 * 1000);
      const localStamp = (value: Date) => `${value.getFullYear()}${String(value.getMonth()+1).padStart(2,'0')}${String(value.getDate()).padStart(2,'0')}T${String(value.getHours()).padStart(2,'0')}${String(value.getMinutes()).padStart(2,'0')}00`;
      const escapeIcs = (value: string) => value.replace(/\\/g,'\\\\').replace(/\n/g,'\\n').replace(/,/g,'\\,').replace(/;/g,'\\;');
      const recurrence = item.id === 'outdoor-reapply'
        ? `RRULE:FREQ=DAILY;BYHOUR=${[0, 1, 2, 3].map(step => (hour + step * 2) % 24).join(',')};BYMINUTE=${minute};COUNT=28`
        : 'RRULE:FREQ=WEEKLY;COUNT=4';
      lines.push('BEGIN:VEVENT',`UID:${item.id}-${index}@dermasense.local`,`DTSTAMP:${new Date().toISOString().replace(/[-:]/g,'').split('.')[0]}Z`,`DTSTART:${localStamp(date)}`,`DTEND:${localStamp(end)}`,recurrence,`SUMMARY:${escapeIcs(item.title)}`,`DESCRIPTION:${escapeIcs(`${item.guidance} Rule: ${item.ruleId}`)}`,'END:VEVENT');
    });
    lines.push('END:VCALENDAR');
    const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([lines.join('\r\n')],{type:'text/calendar'})); link.download='dermasense-safe-corner.ics'; link.click(); URL.revokeObjectURL(link.href);
  };
  const hasFieldErrors = Boolean(fieldErrors.age || fieldErrors.diameter);
  const printReport = () => {
    if (hasFieldErrors) {
      setReportError('Correct the highlighted age or diameter before printing this summary.');
      return;
    }
    setReportError('');
    window.print();
  };
  const downloadReport = async () => {
    if (hasFieldErrors) {
      setReportError('Correct the highlighted age or diameter before saving this summary.');
      return;
    }
    setReportError('');
    setIsSavingPdf(true);
    try {
    const { jsPDF } = await import('jspdf');
    const doc = new jsPDF({ unit: 'pt', format: 'letter' });
    const margin = 48;
    const pageHeight = doc.internal.pageSize.getHeight();
    const pageWidth = doc.internal.pageSize.getWidth();
    let y = 52;
    const write = (text: string, size = 9, bold = false, gap = 14) => {
      doc.setFont('helvetica', bold ? 'bold' : 'normal');
      doc.setFontSize(size);
      doc.setTextColor(36, 65, 61);
      const lines = doc.splitTextToSize(text, pageWidth - margin * 2) as string[];
      for (const line of lines) {
        if (y > pageHeight - margin) {
          doc.addPage();
          y = margin;
        }
        doc.text(line, margin, y);
        y += gap;
      }
    };
    const section = (title: string) => {
      y += 8;
      write(title.toUpperCase(), 10, true, 15);
    };
    const display = (value: string) => value || 'Not provided';
    write('DermaSense AI', 21, true, 26);
    write('Visit preparation summary', 13, true, 19);
    write(`Prepared ${new Date().toLocaleString()} · Report ID DS-${Date.now().toString(36).toUpperCase()}`, 8, false, 12);
    section('Screening status');
    write('No AI screening result is available. This prototype has no trained model connected and has not analyzed the image. No diagnosis, risk estimate, confidence score, or image explanation was generated.');
    section('Visit notes');
    const details: Array<[string, string]> = [
      ['Initials', display(intake.initials)],
      ['Age', display(intake.age)],
      ['Gender', display(intake.gender)],
      ['Fitzpatrick skin type', intake.fitzpatrick === 'unknown' ? 'I don’t know' : display(intake.fitzpatrick)],
      ['Body region', display(intake.region)],
      ['Lesion diameter', intake.diameter ? `${intake.diameter} mm` : 'Not provided'],
      ['Smoking exposure', display(intake.smoking)],
      ['Alcohol exposure', display(intake.alcohol)],
      ['Pesticide exposure', display(intake.pesticide)],
      ['Personal skin-cancer history', display(intake.personalCancer)],
      ['Family cancer history', display(intake.familyCancer)],
      ['Itch', display(intake.itch)],
      ['Growth', display(intake.growth)],
      ['Pain', display(intake.pain)],
      ['Changed in appearance', display(intake.change)],
      ['Bleeding', display(intake.bleeding)],
      ['Raised / elevated', display(intake.elevation)],
    ];
    details.forEach(([label, value]) => write(`${label}: ${value}`, 9, false, 13));
    if (image) {
      section('Uploaded image');
      write(`${image.fileName} · ${image.width} × ${image.height} px · local browser file`);
      try {
        const blob = await fetch(image.previewUrl).then(response => response.blob());
        const dataUrl = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result));
          reader.onerror = () => reject(new Error('Could not prepare the local image for this report.'));
          reader.readAsDataURL(blob);
        });
        if (y + 190 > pageHeight - margin) {
          doc.addPage();
          y = margin;
        }
        doc.addImage(dataUrl, image.mime === 'image/png' ? 'PNG' : 'JPEG', margin, y, 180, 180, undefined, 'FAST');
        y += 194;
      } catch {
        write('The local image could not be embedded in this PDF. It remains on this device.');
      }
    }
    section('Screening-only disclaimer');
    write('This is a screening-support prototype, not a diagnostic device and not a substitute for professional medical care. No diagnosis, risk estimate, or treatment recommendation is provided. Please discuss skin concerns with a qualified clinician. If a spot is rapidly changing, bleeding, painful, or otherwise concerning, seek medical advice.', 9, false, 13);
    write('Privacy: personal details and the image stay in this browser session. This PDF is saved only to your device.', 8, false, 12);
    doc.save('dermasense-visit-summary.pdf');
    } catch {
      setReportError('Could not create the PDF. Please try printing the summary instead.');
    } finally {
      setIsSavingPdf(false);
    }
  };
  const navLinks = [['Visit prep','#visit'],['Safe Corner','#safe-corner'],['About','#about']];

  return <div className="min-h-[100dvh] bg-[#f6f4ec] text-[#24413d]">
    <header className="no-print sticky top-0 z-20 border-b border-[#deddd2] bg-[#f8f7f1]/95 backdrop-blur">
      <div className="mx-auto flex h-[72px] max-w-[1240px] items-center justify-between px-5 md:px-8">
        <a href="#top" className="flex items-center gap-3 no-underline" aria-label="DermaSense AI home">
          <span className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-[#24554e] text-[#f8f5e9]"><Activity size={20}/></span>
          <span><span className="block serif text-[19px] font-extrabold tracking-[-.055em]">DermaSense<span className="text-[#b26d58]"> AI</span></span><span className="block text-[10px] font-bold uppercase tracking-[.15em] text-[#78837b]">A visit-prep companion</span></span>
        </a>
        <nav className="hidden items-center gap-8 md:flex" aria-label="Main navigation">
          {navLinks.map(([label,href])=><a data-testid={`link-${label.toLowerCase().replaceAll(' ','-')}`} key={href} className="text-[13px] font-semibold text-[#586c66] no-underline transition hover:text-[#24554e]" href={href}>{label}</a>)}
          <a href="#report" className="rounded-full bg-[#24554e] px-5 py-2.5 text-[13px] font-bold text-[#faf8ed] no-underline transition hover:bg-[#183f39]">Your summary <ArrowRight className="ml-1 inline" size={15}/></a>
        </nav>
        <button type="button" aria-label="Toggle navigation" className="rounded-lg p-2 md:hidden" onClick={()=>setMobileOpen(!mobileOpen)}><Menu/></button>
      </div>
      {mobileOpen && <nav className="grid gap-1 border-t border-[#deddd2] px-5 py-3 md:hidden">{navLinks.map(([label,href])=><a key={href} href={href} onClick={()=>setMobileOpen(false)} className="rounded-lg px-3 py-2 text-sm font-semibold text-[#42635c] no-underline">{label}</a>)}</nav>}
    </header>

    <main id="top" className="page-enter">
      <section className="relative overflow-hidden border-b border-[#deddd2]">
        <div className="pointer-events-none absolute -right-24 -top-32 h-[440px] w-[440px] rounded-full border border-[#d6d8c9] opacity-70"/><div className="pointer-events-none absolute -right-3 -top-12 h-[300px] w-[300px] rounded-full border border-[#d6d8c9] opacity-60"/>
        <div className="mx-auto grid max-w-[1240px] gap-8 px-5 pb-12 pt-12 md:grid-cols-[1.12fr_.88fr] md:items-center md:px-8 md:pb-16 md:pt-16">
          <div>
            <div className="mb-5 flex w-fit items-center gap-2 rounded-full border border-[#cbd8cd] bg-[#e8eee5] px-3 py-1.5 text-[10px] font-bold uppercase tracking-[.15em] text-[#37635a]"><ShieldCheck size={13}/>Private by design · screening support only</div>
            <h1 className="serif max-w-[650px] text-[clamp(2.8rem,6vw,5rem)] font-semibold leading-[.99] tracking-[-.065em] text-[#1f443e]">A clearer start to your <span className="text-[#b06f5b]">skin check.</span></h1>
            <p className="mt-5 max-w-[540px] text-[15px] leading-7 text-[#64756e]">Gather the details you may want for a clinician visit. Your notes stay here in this browser session—and no AI result is available in this prototype.</p>
            <div className="mt-7 flex flex-wrap items-center gap-3">
              <a href="#visit" className="inline-flex items-center gap-2 rounded-full bg-[#24554e] px-6 py-3.5 text-sm font-bold text-[#faf8ed] no-underline shadow-[0_8px_20px_rgba(31,74,66,.15)] transition hover:-translate-y-0.5 hover:bg-[#183f39]">Start visit prep <ArrowRight size={16}/></a>
              <a href="#safe-corner" className="px-4 py-3 text-sm font-semibold text-[#45655e] no-underline">Explore Safe Corner <ArrowDownToLine className="ml-1 inline" size={15}/></a>
            </div>
            <div className="mt-8 flex items-center gap-3 text-[12px] text-[#687b73]"><LockKeyhole size={15} className="text-[#477166]"/>No account. No upload to a server. Clear this session by refreshing or closing the tab.</div>
          </div>
          <div className="relative mx-auto w-full max-w-[480px]">
            <div className="absolute inset-5 rounded-[46%_54%_59%_41%/41%_43%_57%_59%] bg-[#dce6d7]"/>
            <div className="relative flex aspect-[1.12] items-center justify-center">
              <div className="absolute left-[15%] top-[12%] h-16 w-16 rounded-full border border-[#b5c9bb]"/>
              <div className="absolute right-[14%] top-[20%] h-2 w-2 rounded-full bg-[#b26d58]"/>
              <div className="absolute bottom-[17%] left-[12%] h-2 w-2 rounded-full bg-[#789786]"/>
              <div className="relative flex h-[68%] w-[68%] items-center justify-center rounded-[50%] border border-[#b7c9bb] bg-[#eff1e8] shadow-[0_25px_60px_rgba(45,83,72,.10)]">
                <div className="absolute inset-[12%] rounded-[50%] border border-dashed border-[#b9cabb]"/>
                <div className="flex h-[64%] w-[64%] items-center justify-center rounded-full bg-[#dce7d8]"><div className="flex h-[78%] w-[78%] items-center justify-center rounded-full border border-[#adc1b2] bg-[#eff2e9]"><span className="h-5 w-5 rounded-full border-[5px] border-[#ae765f] bg-[#dca58c] shadow-[0_0_0_10px_rgba(174,118,95,.12)]"/></div></div>
                <div className="absolute bottom-[5%] right-[-6%] rounded-[18px] border border-[#e1dfd3] bg-[#fcfbf5] px-4 py-3 shadow-[0_10px_28px_rgba(45,83,72,.08)]"><div className="flex items-center gap-2 text-[11px] font-bold text-[#41645c]"><CheckCircle2 size={15}/>Your notes, your browser</div><div className="mt-1 pl-[23px] text-[10px] text-[#829088]">No diagnosis generated</div></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="visit" className="scroll-mt-24 mx-auto max-w-[1240px] px-5 py-12 md:px-8 md:py-16">
        <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div><p className="mb-2 text-[11px] font-bold uppercase tracking-[.17em] text-[#b06f5b]">Your visit preparation</p><h2 className="serif text-3xl font-semibold tracking-[-.045em] md:text-[40px]">A few details, at your pace.</h2></div>
          <div className="flex items-center gap-2 text-xs text-[#6b7c74]"><span className="h-2 w-2 rounded-full bg-[#8aa595]"/>Optional fields · “I don’t know” is always okay</div>
        </div>
        <div className="mb-7 rounded-2xl border border-[#cdd9ce] bg-[#eaf0e8] px-4 py-4 md:px-5">
          <label className="flex cursor-pointer items-start gap-3">
            <input data-testid="input-consent" className="mt-1 h-4 w-4 accent-[#24554e]" type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>
            <span><strong className="block text-sm font-bold text-[#2c534a]">A note about this prototype</strong><span className="mt-1 block text-[13px] leading-5 text-[#5f7269]">I understand this tool does not diagnose, assess risk, or replace a clinician. The image and personal details I enter are held only in this browser session and are not sent to a server.</span></span>
          </label>
        </div>
        {!consent && <div className="mb-7 flex items-center gap-2 text-xs text-[#728078]"><Info size={15}/>Please review and acknowledge the privacy and screening note before adding visit details or an image.</div>}
        <div className={`grid gap-6 lg:grid-cols-[1.16fr_.84fr] ${!consent?'opacity-65':''}`} aria-disabled={!consent}>
          <div className="rounded-[24px] border border-[#deddd2] bg-[#fcfbf6] p-5 shadow-[0_8px_24px_rgba(60,79,64,.035)] md:p-7">
            <div className="mb-6 flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#e8eee5] text-[#3e6b5f]"><ClipboardList size={19}/></span><div><h3 className="serif text-[21px] font-bold tracking-[-.04em]">Visit notes</h3><p className="text-xs text-[#77837c]">Share only what feels comfortable.</p></div></div>
            <fieldset disabled={!consent} className="space-y-6 border-0 p-0">
              <div className="grid gap-4 sm:grid-cols-3">
                <Field label="Initials" hint="Optional"><input data-testid="input-initials" value={intake.initials} onChange={e=>change('initials',e.target.value)} maxLength={4} placeholder="e.g. A.B."/></Field>
                <Field label="Age"><><input data-testid="input-age" type="number" min="0" max="120" value={intake.age} onChange={e=>change('age',e.target.value)} aria-invalid={Boolean(fieldErrors.age)} placeholder="Age in years"/>{fieldErrors.age&&<span role="alert" className="mt-1 block text-[10px] font-semibold text-[#a4463f]">{fieldErrors.age}</span>}</></Field>
                <Field label="Gender"><select data-testid="select-gender" value={intake.gender} onChange={e=>change('gender',e.target.value)}><option value="">Select / skip</option><option>Woman</option><option>Man</option><option>Non-binary</option><option>Self-describe</option><option>Prefer not to say</option></select></Field>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <Field label="Fitzpatrick skin type" hint="If known"><select data-testid="select-fitzpatrick" value={intake.fitzpatrick} onChange={e=>change('fitzpatrick',e.target.value)}><option value="">Choose / don’t know</option>{[1,2,3,4,5,6].map(n=><option key={n} value={String(n)}>Type {n}</option>)}<option value="unknown">I don’t know</option></select></Field>
                <Field label="Body region"><select data-testid="select-region" value={intake.region} onChange={e=>change('region',e.target.value)}><option value="">Choose / don’t know</option>{['Head or neck','Chest or abdomen','Back','Arm or hand','Leg or foot','Other','I don’t know'].map(v=><option key={v}>{v}</option>)}</select></Field>
                <Field label="Lesion diameter" hint="Approximate, mm"><><input data-testid="input-diameter" type="number" min="0" max="200" step="0.1" value={intake.diameter} onChange={e=>change('diameter',e.target.value)} aria-invalid={Boolean(fieldErrors.diameter)} placeholder="e.g. 4"/>{fieldErrors.diameter&&<span role="alert" className="mt-1 block text-[10px] font-semibold text-[#a4463f]">{fieldErrors.diameter}</span>}</></Field>
              </div>
              <div className="border-t border-[#e8e6dc] pt-5"><h4 className="mb-1 text-sm font-bold">Background</h4><p className="mb-4 text-xs text-[#79867f]">A quick context for your appointment.</p>
                <div className="grid gap-x-5 gap-y-4 sm:grid-cols-2">
                  <Question label="Smoking exposure" name="smoking" value={intake.smoking} onChange={change}/>
                  <Question label="Alcohol exposure" name="alcohol" value={intake.alcohol} onChange={change}/>
                  <Question label="Pesticide exposure" name="pesticide" value={intake.pesticide} onChange={change}/>
                  <Question label="Personal history of skin cancer" name="personalCancer" value={intake.personalCancer} onChange={change}/>
                  <Question label="Family history of cancer" name="familyCancer" value={intake.familyCancer} onChange={change}/>
                </div>
              </div>
              <div className="border-t border-[#e8e6dc] pt-5"><h4 className="mb-1 text-sm font-bold">About this spot</h4><p className="mb-4 text-xs text-[#79867f]">These are notes only—not a risk score.</p>
                <div className="grid gap-x-5 gap-y-4 sm:grid-cols-2">
                  <Question label="Itch" name="itch" value={intake.itch} onChange={change}/>
                  <Question label="Growing" name="growth" value={intake.growth} onChange={change}/>
                  <Question label="Pain" name="pain" value={intake.pain} onChange={change}/>
                  <Question label="Changed in appearance" name="change" value={intake.change} onChange={change}/>
                  <Question label="Bleeding" name="bleeding" value={intake.bleeding} onChange={change}/>
                  <Question label="Raised / elevated" name="elevation" value={intake.elevation} onChange={change}/>
                </div>
              </div>
            </fieldset>
          </div>
          <div className="space-y-6">
            <div className="rounded-[24px] border border-[#deddd2] bg-[#fcfbf6] p-5 shadow-[0_8px_24px_rgba(60,79,64,.035)] md:p-6">
              <div className="mb-5 flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#f2e7df] text-[#a46250]"><ImagePlus size={19}/></span><div><h3 className="serif text-[21px] font-bold tracking-[-.04em]">Optional image</h3><p className="text-xs text-[#77837c]">JPG or PNG · stays on this device</p></div></div>
              <fieldset disabled={!consent} className="border-0 p-0">
                {!image ? <button data-testid="button-upload-image" type="button" onClick={()=>inputRef.current?.click()} className="group w-full rounded-2xl border border-dashed border-[#aebfb2] bg-[#f4f5ec] px-5 py-8 text-center transition hover:border-[#628b7a] hover:bg-[#eff3e9]">
                  <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#e0e9de] text-[#3f6e5e]"><Upload size={20}/></span><span className="mt-3 block text-sm font-bold">Choose an image</span><span className="mt-1 block text-xs text-[#7b8980]">Browse files from this device</span>
                </button> : <div className="overflow-hidden rounded-2xl border border-[#e3e1d7]">
                  <div className="relative flex h-[210px] items-center justify-center bg-[#e6e8df]"><img src={image.previewUrl} alt="Selected lesion image preview" className="max-h-full max-w-full object-contain"/><button type="button" data-testid="button-remove-image" onClick={clearImage} aria-label="Remove image" className="absolute right-3 top-3 flex h-9 w-9 items-center justify-center rounded-full bg-[#fcfbf6] text-[#4f625b] shadow"><X size={17}/></button></div>
                  <div className="p-4"><div className="truncate text-sm font-bold">{image.fileName}</div><div className="mt-1 text-xs text-[#78867e]">{image.width} × {image.height} px · {image.mime.split('/')[1].toUpperCase()}</div>
                     <div className="mt-3 flex flex-wrap gap-2">{[['Resolution',image.flags.resolution==='good'?'Looks adequate':'Low resolution'],['Lighting',image.flags.brightness==='good'?'Looks balanced':image.flags.brightness==='dim'?'May be dim':image.flags.brightness==='bright'?'May be overexposed':'Could not check lighting'],['Focus',image.flags.blur==='good'?'Edge detail found':'Focus may be soft']].map(([label,value])=><span key={label} className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${value.startsWith('Looks')||value==='Edge detail found'?'bg-[#e6efe5] text-[#3c6d5a]':'bg-[#f4e9dc] text-[#895d3f]'}`}>{label}: {value}</span>)}</div>
                    <p className="mt-3 text-[10px] leading-4 text-[#859087]">Automated checks are approximate, run locally, and do not interpret the lesion.</p>
                  </div>
                </div>}
                <input ref={inputRef} data-testid="input-image-file" type="file" accept="image/jpeg,image/png,.jpg,.jpeg,.png" className="hidden" onChange={e=>upload(e.target.files?.[0])}/>
                {uploadError&&<p role="alert" className="mt-3 text-xs font-semibold text-[#a4463f]">{uploadError}</p>}
              </fieldset>
              <div className="mt-4 flex items-start gap-2 rounded-xl bg-[#f2f0e7] p-3 text-[11px] leading-4 text-[#68766e]"><LockKeyhole size={14} className="mt-0.5 shrink-0 text-[#52766b]"/>Image bytes and preview exist only in this open browser session. They are not uploaded or saved.</div>
            </div>
            <div className="rounded-[24px] border border-[#d5ddcf] bg-[#eaf0e8] p-5 md:p-6">
              <div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#d7e5d8] text-[#416f5f]"><CircleHelp size={19}/></span><div><div className="text-[10px] font-bold uppercase tracking-[.15em] text-[#75867b]">Prototype status</div><h3 className="serif text-lg font-bold tracking-[-.03em]">AI screening is unavailable</h3></div></div>
              <p className="mt-3 text-[13px] leading-5 text-[#5f7269]">There is no trained model connected to this prototype. No inference runs, and no label, confidence, or explanation will be generated.</p>
              <div className="mt-4 flex items-center gap-2 border-t border-[#d4ddd1] pt-3 text-xs font-semibold text-[#3d6859]"><Check size={14}/>Your notes can still help you prepare.</div>
            </div>
          </div>
        </div>
      </section>

      <section id="report" className="scroll-mt-24 border-y border-[#deddd2] bg-[#efeee5]">
        <div className="mx-auto max-w-[1240px] px-5 py-12 md:px-8 md:py-16">
          <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="mb-2 text-[11px] font-bold uppercase tracking-[.17em] text-[#b06f5b]">Your visit summary</p><h2 className="serif text-3xl font-semibold tracking-[-.045em] md:text-[40px]">Useful notes. No guesswork.</h2></div><div className="no-print flex flex-wrap gap-2"><button data-testid="button-print-report" onClick={printReport} type="button" className="inline-flex items-center gap-2 rounded-full border border-[#bfcbbd] bg-[#faf9f2] px-4 py-2.5 text-xs font-bold text-[#375c53] hover:bg-white"><Printer size={15}/>Print</button><button data-testid="button-download-report" onClick={downloadReport} disabled={isSavingPdf} type="button" className="inline-flex items-center gap-2 rounded-full bg-[#24554e] px-4 py-2.5 text-xs font-bold text-[#faf8ed] hover:bg-[#183f39] disabled:opacity-60"><Download size={15}/>{isSavingPdf?'Preparing PDF…':'Save as PDF'}</button></div></div>
          {reportError&&<p className="no-print mb-3 text-xs font-semibold text-[#a4463f]" role="alert">{reportError}</p>}
          <div className="print-area overflow-hidden rounded-[24px] border border-[#d8d8cd] bg-[#fcfbf6] shadow-[0_12px_35px_rgba(54,76,63,.05)]">
            <div className="flex flex-col gap-4 border-b border-[#e7e5da] p-5 md:flex-row md:items-center md:justify-between md:px-7 md:py-6"><div className="flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#e8eee5] text-[#3d6a5b]"><FileText size={20}/></span><div><h3 className="serif text-xl font-bold tracking-[-.04em]">Appointment notes</h3><p className="text-xs text-[#7a8780]">Prepared {new Date().toLocaleDateString()}</p></div></div><div data-testid="status-screening" className="flex w-fit items-center gap-2 rounded-full border border-[#dfcdbb] bg-[#f6eee4] px-3 py-2 text-[11px] font-bold text-[#805e43]"><Info size={14}/>AI result unavailable</div></div>
            <div className="grid gap-0 md:grid-cols-[1fr_.82fr]">
              <div className="p-5 md:px-7 md:py-6"><div className="mb-4 text-[10px] font-bold uppercase tracking-[.16em] text-[#a16a55]">Details for your visit</div><div className="grid grid-cols-2 gap-x-5 gap-y-4 sm:grid-cols-3">{[
                ['Initials',intake.initials||'Not provided'],['Age',intake.age||'Not provided'],['Gender',intake.gender||'Not provided'],['Skin type',intake.fitzpatrick?intake.fitzpatrick==='unknown'?'I don’t know':`Type ${intake.fitzpatrick}`:'Not provided'],['Body region',intake.region||'Not provided'],['Diameter',intake.diameter?`${intake.diameter} mm`:'Not provided']
              ].map(([label,value])=><div key={label}><div className="text-[10px] font-semibold uppercase tracking-[.1em] text-[#8a938c]">{label}</div><div className="mt-1 text-sm font-semibold text-[#38534b]">{value}</div></div>)}</div>
                <div className="mt-5 border-t border-[#e9e7de] pt-4"><div className="mb-3 text-[10px] font-bold uppercase tracking-[.16em] text-[#a16a55]">History notes</div><div className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">{[
                  ['Smoking',intake.smoking],['Alcohol',intake.alcohol],['Pesticides',intake.pesticide],['Personal skin-cancer history',intake.personalCancer],['Family cancer history',intake.familyCancer],['Itch',intake.itch],['Growth',intake.growth],['Pain',intake.pain],['Change',intake.change],['Bleeding',intake.bleeding],['Elevation',intake.elevation]
                ].map(([label,value])=><div className="flex justify-between gap-2 border-b border-[#efeee7] py-1.5 text-[11px]" key={label}><span className="text-[#758178]">{label}</span><span className="font-semibold text-[#405d53]">{value ? value.charAt(0).toUpperCase()+value.slice(1):'—'}</span></div>)}</div></div>
              </div>
              <div className="border-t border-[#e7e5da] bg-[#f6f5ed] p-5 md:border-l md:border-t-0 md:px-6 md:py-6"><div className="text-[10px] font-bold uppercase tracking-[.16em] text-[#a16a55]">Screening status</div><h4 className="serif mt-2 text-xl font-bold tracking-[-.04em]">No result has been produced.</h4><p className="mt-2 text-[13px] leading-5 text-[#687970]">This prototype has no trained model or dataset connected. It has not analyzed your image or estimated risk. Image quality checks are technical checks only.</p>
                {image && <div className="mt-4 flex items-center gap-3 rounded-xl border border-[#e1e0d5] bg-[#fcfbf6] p-3"><img src={image.previewUrl} alt="" className="h-12 w-12 rounded-lg object-cover"/><div className="min-w-0"><div className="truncate text-xs font-bold">{image.fileName}</div><div className="text-[10px] text-[#78867e]">Local image · {image.width} × {image.height}</div></div></div>}
              </div>
            </div>
            <div className="border-t border-[#e7e5da] bg-[#f4ece4] px-5 py-4 md:px-7"><div className="text-[10px] font-bold uppercase tracking-[.15em] text-[#905f4e]">Screening-only disclaimer</div><p className="mt-1 text-[11px] leading-[1.6] text-[#745f53]">This is a screening-support prototype, not a diagnostic device and not a substitute for professional medical care. No diagnosis, risk estimate, or treatment recommendation is provided. Please discuss skin concerns with a qualified clinician. If a spot is rapidly changing, bleeding, painful, or otherwise concerning, seek medical advice.</p></div>
          </div>
          <p className="mt-3 flex items-center gap-2 text-[11px] text-[#7d8981]"><LockKeyhole size={13}/>Personal details and image are held only in this browser session. The PDF is saved to your device only if you choose.</p>
        </div>
      </section>

      <section id="safe-corner" className="scroll-mt-24 mx-auto max-w-[1240px] px-5 py-12 md:px-8 md:py-16">
        <div className="grid gap-9 lg:grid-cols-[.82fr_1.18fr]">
          <div><div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-[#e5eadb] text-[#54715c]"><Heart size={21}/></div><p className="mb-2 text-[11px] font-bold uppercase tracking-[.17em] text-[#b06f5b]">Safe Corner · weekly routine</p><h2 className="serif max-w-[410px] text-3xl font-semibold leading-tight tracking-[-.05em] md:text-[42px]">Small, steady habits for skin wellbeing.</h2><p className="mt-4 max-w-[420px] text-sm leading-6 text-[#6c7a71]">General wellness reminders—not a care plan, diagnosis, or substitute for advice from your clinician. Your check-offs are saved locally on this device.</p>
            {storageWarning&&<p className="mt-3 max-w-sm text-xs font-semibold leading-5 text-[#9a5847]" role="status">{storageWarning}</p>}
            <div className="mt-5 grid max-w-sm grid-cols-2 gap-3">
              <label className="text-[11px] font-bold text-[#586c63]">Wake time<input data-testid="input-wake-time" type="time" value={wakeTime} onChange={e=>setWakeTime(e.target.value)} className="mt-1 block w-full rounded-lg border border-[#d6dbcf] bg-[#fcfbf6] px-3 py-2 text-sm font-normal"/></label>
              <label className="text-[11px] font-bold text-[#586c63]">Sleep time<input data-testid="input-sleep-time" type="time" value={sleepTime} onChange={e=>setSleepTime(e.target.value)} className="mt-1 block w-full rounded-lg border border-[#d6dbcf] bg-[#fcfbf6] px-3 py-2 text-sm font-normal"/></label>
            </div>
            <button data-testid="button-export-calendar" onClick={addCalendar} className="no-print mt-6 inline-flex items-center gap-2 rounded-full border border-[#bfcbbd] bg-[#fcfbf6] px-5 py-3 text-sm font-bold text-[#3c6557] transition hover:bg-[#eaf0e8]" type="button"><CalendarDays size={16}/>Add reminders to calendar <ArrowRight size={15}/></button>
            <div className="mt-5 flex items-start gap-2 text-[11px] leading-4 text-[#7a887e]"><Info size={14} className="mt-0.5 shrink-0"/>Calendar export creates scheduled reminders on your device. Review timing and guidance with a healthcare professional if needed.</div>
          </div>
          <div className="overflow-hidden rounded-[24px] border border-[#deddd2] bg-[#fcfbf6]">
            <div className="flex items-center justify-between border-b border-[#e7e5da] px-5 py-4"><div><div className="text-[10px] font-bold uppercase tracking-[.16em] text-[#a16a55]">This week</div><div className="serif mt-1 text-xl font-bold tracking-[-.04em]">A gentle checklist</div></div><div className="rounded-full bg-[#eaf0e8] px-3 py-1.5 text-[11px] font-bold text-[#426c5d]">{routine.filter(x=>x.checked).length} of {routine.length} done</div></div>
            <div className="divide-y divide-[#eceae1]">{routine.map(item=><label key={item.id} className={`flex cursor-pointer gap-4 px-5 py-4 transition hover:bg-[#f8f7f0] ${item.checked?'opacity-70':''}`}><input data-testid={`checkbox-routine-${item.id}`} type="checkbox" checked={item.checked} onChange={()=>toggleRoutine(item.id)} className="peer sr-only"/><span className={`mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition ${item.checked?'border-[#4a7967] bg-[#4a7967] text-white':'border-[#c7cec1] bg-transparent text-transparent'}`}><Check size={13}/></span><span className="min-w-0 flex-1"><span className="flex flex-wrap items-baseline justify-between gap-2"><span className="text-[10px] font-bold uppercase tracking-[.14em] text-[#a16a55]">{item.time} · {scheduledTime(item.id)}</span><span className="font-mono text-[9px] text-[#a0a69d]">{item.ruleId}</span></span><span className="mt-1 block text-sm font-bold text-[#335149]">{item.title}</span><span className="mt-1 block text-xs leading-[1.55] text-[#748078]">{item.guidance}</span></span></label>)}</div>
            <div className="flex items-center justify-between gap-3 border-t border-[#e7e5da] bg-[#f6f5ed] px-5 py-3"><span className="text-[10px] text-[#889188]">Check-offs are stored locally, not synced.</span><button data-testid="button-reset-routine" type="button" onClick={()=>setRoutine(items=>items.map(i=>({...i,checked:false})))} className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-[11px] font-bold text-[#61766a] hover:bg-white"><RotateCcw size={12}/>Reset week</button></div>
          </div>
        </div>
      </section>

      <section id="about" className="border-t border-[#deddd2] bg-[#e9eee5]">
        <div className="mx-auto grid max-w-[1240px] gap-8 px-5 py-10 md:grid-cols-[1fr_auto] md:items-center md:px-8">
          <div><div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[.16em] text-[#54766a]"><ShieldCheck size={15}/>Built around transparency</div><p className="serif mt-2 max-w-[740px] text-[19px] font-semibold leading-7 tracking-[-.025em] text-[#31534a]">A thoughtful place to organize what you’ve noticed—not a machine that tells you what it means.</p><p className="mt-2 text-xs text-[#728078]">No model inference · no server upload · no medical advice generated</p></div>
          <a href="#visit" className="no-print inline-flex w-fit items-center gap-2 rounded-full bg-[#24554e] px-5 py-3 text-xs font-bold text-[#faf8ed] no-underline hover:bg-[#183f39]">Back to visit prep <ArrowRight size={14}/></a>
        </div>
      </section>
    </main>
    <footer className="bg-[#24443e] text-[#dce7da]"><div className="mx-auto flex max-w-[1240px] flex-col gap-4 px-5 py-6 text-[11px] md:flex-row md:items-center md:justify-between md:px-8"><div className="flex items-center gap-2 font-semibold"><Activity size={14}/>DermaSense AI</div><div className="max-w-xl leading-5 text-[#b7c8ba]">Screening-support prototype only. Not a diagnostic device. Seek qualified medical advice for skin concerns.</div><div className="text-[#a5b7a8]">Your session data stays here.</div></div></footer>
  </div>;
}

function Field({label,hint,children}:{label:string;hint?:string;children:ReactNode}) {
  return <label className="block"><span className="mb-1.5 flex items-baseline justify-between gap-2 text-xs font-bold text-[#455d54]">{label}{hint&&<span className="text-[10px] font-normal text-[#8b958c]">{hint}</span>}</span>{children}</label>;
}
function Question({label,name,value,onChange}:{label:string;name:keyof Intake;value:Answer;onChange:(key:keyof Intake,value:string)=>void}) {
  return <fieldset className="border-0 p-0"><legend className="mb-2 text-xs font-semibold text-[#566b61]">{label}</legend><div className="flex gap-1.5">{(['yes','no','unknown'] as const).map(item=><button data-testid={`answer-${name}-${item}`} key={item} type="button" aria-pressed={value===item} onClick={()=>onChange(name,value===item?'':item)} className={`rounded-full border px-3 py-1.5 text-[10px] font-semibold capitalize transition ${value===item?'border-[#608573] bg-[#e5eee4] text-[#315f50]':'border-[#e1e1d8] bg-[#faf9f3] text-[#7a867d] hover:border-[#b6c6b6]'}`}>{item==='unknown'?'I don’t know':item}</button>)}</div></fieldset>;
}
function RoutedErrorBoundary({children}:{children:ReactNode}) { const [location] = useLocation(); return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>; }
function Router() { return <RoutedErrorBoundary><Switch><Route path="/" component={App}/><Route component={NotFound}/></Switch></RoutedErrorBoundary>; }
function Root() { return <QueryClientProvider client={queryClient}><TooltipProvider><WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/,'')}><Router/></WouterRouter><Toaster/></TooltipProvider></QueryClientProvider>; }
export default Root;
