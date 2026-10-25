import { useEffect, useMemo, useRef, useState, createContext, useContext, type ComponentType, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Link, Route, Switch, Router as WouterRouter, useLocation } from 'wouter';
import {
  ArrowDownRight, ArrowRight, Bell, Check, ChevronDown, Download, Eye, FolderClock,
  Gauge, HelpCircle, LayoutDashboard, LockKeyhole, Mic2, MoreHorizontal, Palette, Play,
  Plus, RotateCcw, Scissors, Search, Send, Settings2, Share2, SlidersHorizontal, Sparkles,
  UploadCloud, UserRound, WandSparkles, Volume2, X, Zap,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const queryClient = new QueryClient();

type IconType = ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
type Toast = { id: number; message: string; tone: 'success' | 'info' };

const styles = [
  { id: 'neon-noir', name: 'Neon Noir', type: 'Cinematic', tag: 'Most used', description: 'Electric shadows, high-contrast cuts, and a little danger.', gradient: 'linear-gradient(135deg, #0A0A0A 0%, #FF307F 48%, #2B59FF 100%)', icon: 'NN', stat: '12.4k edits' },
  { id: 'soft-focus', name: 'Soft Focus', type: 'Lifestyle', tag: 'New', description: 'Slow breath, warm grain, and moments that linger.', gradient: 'linear-gradient(135deg, #0A0A0A 0%, #FF7A00 50%, #FFD400 100%)', icon: 'SF', stat: '8.1k edits' },
  { id: 'street-cut', name: 'Street Cut', type: 'Fast / Raw', tag: 'Trending', description: 'Hard cuts, kinetic type, and an unapologetic pulse.', gradient: 'linear-gradient(135deg, #0A0A0A 0%, #FF307F 50%, #FFD400 100%)', icon: 'SC', stat: '9.7k edits' },
  { id: 'quiet-luxury', name: 'Quiet Luxury', type: 'Editorial', tag: 'Pro pick', description: 'A composed edit for ideas that deserve the room.', gradient: 'linear-gradient(135deg, #0A0A0A 0%, #2B59FF 52%, #00B37E 100%)', icon: 'QL', stat: '5.6k edits' },
  { id: 'chromatic', name: 'Chromatic', type: 'Music / Art', tag: 'Experimental', description: 'Color that moves with the beat. No two frames feel alike.', gradient: 'linear-gradient(135deg, #2B59FF 0%, #FF307F 50%, #FFD400 100%)', icon: 'CH', stat: '4.3k edits' },
  { id: 'after-hours', name: 'After Hours', type: 'Nightlife', tag: 'Community', description: 'Deep blacks, blown highlights, and a 2am kind of confidence.', gradient: 'linear-gradient(135deg, #0A0A0A 0%, #FF307F 42%, #FF7A00 100%)', icon: 'AH', stat: '7.2k edits' },
];

const projects = [
  { id: 'p1', title: 'The city is still awake', style: 'Neon Noir', time: 'Just now', duration: '00:42', status: 'Ready', gradient: 'linear-gradient(135deg, #0A0A0A 0%, #FF307F 55%, #2B59FF 100%)' },
  { id: 'p2', title: 'Sunday, in three frames', style: 'Soft Focus', time: 'Yesterday', duration: '01:08', status: 'Ready', gradient: 'linear-gradient(135deg, #0A0A0A 0%, #FF7A00 50%, #FFD400 100%)' },
  { id: 'p3', title: 'No shortcuts to the top', style: 'Street Cut', time: 'Mar 18', duration: '00:27', status: 'Draft', gradient: 'linear-gradient(135deg, #0A0A0A 0%, #FF307F 50%, #FFD400 100%)' },
  { id: 'p4', title: 'Notes from a blue room', style: 'Quiet Luxury', time: 'Mar 14', duration: '00:56', status: 'Ready', gradient: 'linear-gradient(135deg, #0A0A0A 0%, #2B59FF 50%, #00B37E 100%)' },
];

const navItems: { href: string; label: string; icon: IconType }[] = [
  { href: '/', label: 'Overview', icon: LayoutDashboard },
  { href: '/create', label: 'Create edit', icon: Plus },
  { href: '/styles', label: 'Trends', icon: Palette },
  { href: '/projects', label: 'Projects', icon: FolderClock },
];
const utilityItems: { href: string; label: string; icon: IconType }[] = [
  { href: '/preferences', label: 'Preferences', icon: SlidersHorizontal },
  { href: '/profile', label: 'Profile', icon: UserRound },
  { href: '/settings', label: 'Settings', icon: Settings2 },
];

/* ── Maximalist Animation Helpers ── */
function Wiggle({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      whileHover={{ rotate: [0, -3, 3, -1, 0] }}
      transition={{ duration: 0.4 }}
      className={className ? className : 'inline-block'}
    >
      {children}
    </motion.div>
  );
}

function Starburst({
  text = '★',
  size = '3.5rem',
  className = '',
  color = '#FFD400',
  textColor = '#0A0A0A',
}: {
  text?: string;
  size?: string;
  className?: string;
  color?: string;
  textColor?: string;
}) {
  return (
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
      className={`starburst shrink-0 select-none font-bold text-center ${className}`}
      style={{ width: size, height: size, background: color, color: textColor }}
    >
      <span className="text-[10px] font-black uppercase tracking-tight px-1">{text}</span>
    </motion.div>
  );
}

function Sticker({
  emoji,
  className = '',
  size = '2.75rem',
  rotate = 0,
}: {
  emoji: string;
  className?: string;
  size?: string;
  rotate?: number;
}) {
  return (
    <motion.div
      animate={{ y: [0, -6, 0], rotate: [rotate, rotate + 6, rotate - 6, rotate] }}
      transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
      className={`absolute z-20 flex items-center justify-center border-4 border-[#FFD400] bg-[#FF307F] shadow-[0_4px_20px_rgba(255,48,127,0.5)] select-none pointer-events-none ${className}`}
      style={{ width: size, height: size }}
    >
      <span className="text-xl leading-none">{emoji}</span>
    </motion.div>
  );
}

const ToastContext = createContext<(message: string, tone?: Toast['tone']) => void>(() => undefined);
const useNotify = () => useContext(ToastContext);

function ToastStack({ toasts, dismiss }: { toasts: Toast[]; dismiss: (id: number) => void }) {
  return (
    <div className="fixed bottom-5 right-5 z-[120] flex w-[min(380px,calc(100vw-40px))] flex-col gap-3">
      <AnimatePresence>
        {toasts.map((item) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 30, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 60, scale: 0.9 }}
            transition={{ duration: 0.25 }}
          >
            <button
              type="button"
              onClick={() => dismiss(item.id)}
              data-testid={`toast-${item.id}`}
              className={`glass-max flex w-full items-center gap-3 p-4 text-left text-sm border-4 ${
                item.tone === 'success'
                  ? 'border-[#00B37E] shadow-[0_8px_25px_rgba(0,179,126,0.4)]'
                  : 'border-[#FF307F] shadow-[0_8px_25px_rgba(255,48,127,0.4)]'
              }`}
            >
              <span
                className={`grid h-8 w-8 shrink-0 place-items-center font-black ${
                  item.tone === 'success' ? 'bg-[#00B37E] text-[#0A0A0A]' : 'bg-[#FF307F] text-[#0A0A0A]'
                }`}
              >
                {item.tone === 'success' ? <Check size={18} strokeWidth={3} /> : <Sparkles size={18} strokeWidth={3} />}
              </span>
              <span className="flex-1 font-bold text-[#F5F0E8]">{item.message}</span>
              <X size={16} className="text-[#F5F0E8]/60 hover:text-[#FFD400]" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

function Logo() {
  return (
    <Wiggle>
      <Link href="/" className="group flex items-center gap-3" data-testid="link-logo">
        <span className="relative grid h-10 w-10 place-items-center border-3 border-[#FFD400] bg-[#FF307F] text-[#0A0A0A] shadow-[0_4px_0_#2B59FF]">
          <Scissors size={20} strokeWidth={3} />
        </span>
        <span className="font-display text-2xl tracking-tight text-[#F5F0E8] group-hover:text-[#FFD400] transition-colors">
          StyleCut <span className="font-headline text-xl text-[#FF307F]">AI</span>
        </span>
      </Link>
    </Wiggle>
  );
}

function Shell({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  const notify = useNotify();
  return (
    <div className="noise min-h-[100dvh] overflow-x-hidden bg-[#0A0A0A] text-[#F5F0E8]">
      <div className="pointer-events-none fixed -left-40 top-[-140px] h-[500px] w-[500px] bg-[#FF307F]/15 blur-[140px]" />
      <div className="pointer-events-none fixed bottom-[-180px] right-[-90px] h-[480px] w-[480px] bg-[#2B59FF]/15 blur-[140px]" />

      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[260px] flex-col border-r-4 border-[#FF307F] bg-[#0A0A0A] px-5 py-6 pattern-stripes md:flex">
        <Sticker emoji="✂️" className="-top-2 right-4" rotate={12} size="2.5rem" />
        <Logo />

        <div className="mt-10 px-2 text-[10px] font-black uppercase tracking-[.3em] text-[#FF7A00]">
          Workspace
        </div>
        <nav className="mt-3 space-y-1.5" aria-label="Primary navigation">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = href === '/' ? location === '/' : location.startsWith(href);
            return (
              <Wiggle key={href} className="w-full">
                <Link
                  href={href}
                  data-testid={`link-nav-${label.toLowerCase().replaceAll(' ', '-')}`}
                  className={`group flex w-full items-center gap-3 border-2 px-3.5 py-3 text-xs font-bold uppercase tracking-wider transition-all ${
                    active
                      ? 'border-[#FFD400] bg-[#FF307F] text-[#0A0A0A] shadow-[0_4px_0_#2B59FF]'
                      : 'border-transparent text-[#F5F0E8]/70 hover:border-white/20 hover:bg-[#2B59FF]/20 hover:text-[#FFD400]'
                  }`}
                >
                  <Icon size={18} strokeWidth={active ? 2.8 : 2} />
                  <span>{label}</span>
                  {label === 'Create edit' && (
                    <span className="ml-auto border border-[#0A0A0A] bg-[#FFD400] px-1.5 py-0.5 font-mono text-[9px] font-black text-[#0A0A0A]">
                      ⌘N
                    </span>
                  )}
                </Link>
              </Wiggle>
            );
          })}
        </nav>

        <div className="relative mt-7 px-2 text-[10px] font-black uppercase tracking-[.3em] text-[#FF7A00]">
          Your Space
          <Sticker emoji="⚡" className="-top-3 right-2" rotate={-10} size="2.25rem" />
        </div>
        <nav className="mt-3 space-y-1.5">
          {utilityItems.map(({ href, label, icon: Icon }) => {
            const active = location.startsWith(href);
            return (
              <Wiggle key={href} className="w-full">
                <Link
                  href={href}
                  data-testid={`link-nav-${label.toLowerCase()}`}
                  className={`group flex w-full items-center gap-3 border-2 px-3.5 py-2.5 text-xs font-bold uppercase tracking-wider transition-all ${
                    active
                      ? 'border-[#FFD400] bg-[#2B59FF] text-[#F5F0E8] shadow-[0_4px_0_#FF307F]'
                      : 'border-transparent text-[#F5F0E8]/70 hover:border-white/20 hover:bg-white/5 hover:text-[#F5F0E8]'
                  }`}
                >
                  <Icon size={18} strokeWidth={2} />
                  <span>{label}</span>
                </Link>
              </Wiggle>
            );
          })}
        </nav>

        <div className="relative mt-auto">
          <Sticker emoji="💎" className="-top-4 right-3" rotate={18} size="2.5rem" />
          <div className="border-4 border-[#FFD400] bg-[#0A0A0A] p-4 shadow-[0_6px_0_#FF307F]">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-black uppercase tracking-wider text-[#FFD400]">
                Creator Plan
              </span>
              <Zap size={16} className="text-[#FF307F]" />
            </div>
            <div className="mt-3 flex items-end justify-between font-mono text-xs font-bold text-[#F5F0E8]">
              <span>18.4 / 25 min</span>
              <span className="text-[10px] uppercase text-[#F5F0E8]/50">this month</span>
            </div>
            <div className="mt-2.5 h-2.5 overflow-hidden border border-white/20 bg-[#111111]">
              <div
                className="h-full w-[74%]"
                style={{ background: 'linear-gradient(90deg, #FF307F, #FFD400, #2B59FF)' }}
              />
            </div>
            <Wiggle>
              <button
                type="button"
                onClick={() => notify('Creator plan details are ready for your review.', 'info')}
                data-testid="button-view-plan"
                className="mt-3 text-xs font-bold uppercase tracking-wider text-[#FFD400] hover:text-[#FF307F]"
              >
                View plan <ArrowRight size={13} className="ml-1 inline" />
              </button>
            </Wiggle>
          </div>
          <Wiggle className="w-full">
            <button
              type="button"
              onClick={() => notify('No new notifications.', 'info')}
              data-testid="button-notifications"
              className="mt-3 flex w-full items-center gap-3 border-2 border-white/10 bg-[#111111] px-3.5 py-2.5 text-left text-xs font-bold uppercase tracking-wider text-[#F5F0E8]/70 hover:border-[#FF307F] hover:text-[#F5F0E8]"
            >
              <Bell size={16} />
              <span>Notifications</span>
              <span className="ml-auto h-2 w-2 bg-[#00B37E] pulse-dot" />
            </button>
          </Wiggle>
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex h-[74px] items-center justify-between border-b-4 border-[#FFD400] bg-[#0A0A0A]/95 px-5 backdrop-blur-xl md:ml-[260px] md:px-10">
        <div className="md:hidden">
          <Logo />
        </div>
        <div className="hidden items-center gap-2.5 font-bold uppercase tracking-wider text-xs text-[#F5F0E8]/60 md:flex">
          <span className="h-2 w-2 bg-[#00B37E] pulse-dot" />
          <span>Studio /</span>
          <span className="text-[#FF307F] font-black">
            {location === '/' ? 'Overview' : location.slice(1).replace('-', ' ')}
          </span>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <Wiggle>
            <button
              type="button"
              onClick={() => notify('Search is ready — try “city”, “neon”, or “draft”.', 'info')}
              data-testid="button-search"
              className="hidden h-10 items-center gap-2.5 border-2 border-[#2B59FF] bg-[#111111] px-3.5 text-xs font-bold uppercase tracking-wider text-[#F5F0E8]/70 hover:bg-[#2B59FF] hover:text-[#0A0A0A] sm:flex"
            >
              <Search size={15} />
              <span>Search</span>
              <span className="border border-white/20 bg-[#0A0A0A] px-1.5 py-0.5 font-mono text-[10px] text-[#FFD400]">
                ⌘K
              </span>
            </button>
          </Wiggle>
          <Wiggle>
            <button
              type="button"
              onClick={() => notify('You are all caught up.', 'success')}
              data-testid="button-header-notifications"
              className="relative grid h-10 w-10 place-items-center border-2 border-[#FF307F] bg-[#111111] text-[#F5F0E8] hover:bg-[#FF307F] hover:text-[#0A0A0A] transition-colors"
            >
              <Bell size={16} />
              <span className="absolute right-2 top-2 h-2 w-2 bg-[#FFD400]" />
            </button>
          </Wiggle>
          <Wiggle>
            <Link
              href="/profile"
              data-testid="link-header-profile"
              className="flex items-center gap-2.5 border-2 border-[#FFD400] bg-[#111111] p-1.5 pr-3 hover:bg-white/5 transition-all"
            >
              <span className="grid h-8 w-8 place-items-center border-2 border-[#0A0A0A] bg-[#FF307F] font-display text-xs font-bold text-[#0A0A0A]">
                AR
              </span>
              <span className="hidden text-xs font-bold uppercase tracking-wider text-[#F5F0E8] lg:block">
                Ari Rivera
              </span>
              <ChevronDown size={14} className="hidden text-[#FFD400] lg:block" />
            </Link>
          </Wiggle>
        </div>
      </header>

      <main className="relative ml-0 px-5 pb-28 pt-8 md:ml-[260px] md:px-10 md:pb-16 md:pt-10">
        {children}
      </main>

      <nav className="fixed bottom-0 left-0 right-0 z-50 flex border-t-4 border-[#2B59FF] bg-[#0A0A0A]/95 px-2 py-2 backdrop-blur-xl md:hidden">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = href === '/' ? location === '/' : location.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              data-testid={`link-mobile-${label.toLowerCase().replaceAll(' ', '-')}`}
              className={`flex flex-1 flex-col items-center gap-1 py-1.5 text-[10px] font-bold uppercase tracking-wider ${
                active ? 'bg-[#FF307F] text-[#0A0A0A]' : 'text-[#F5F0E8]/60'
              }`}
            >
              <Icon size={18} strokeWidth={2.5} />
              <span>{label === 'Create edit' ? 'Create' : label.split(' ')[0]}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

function PageTitle({
  eyebrow,
  title,
  copy,
  action,
}: {
  eyebrow: string;
  title: ReactNode;
  copy?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-10 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <div className="mb-3 flex items-center gap-2 font-mono text-xs font-black uppercase tracking-[.3em] text-[#FF7A00]">
          <span className="h-1.5 w-6 bg-[#FF7A00]" />
          {eyebrow}
        </div>
        <h1 className="leading-tight text-[#F5F0E8]">{title}</h1>
        {copy && (
          <p className="mt-4 max-w-2xl text-sm leading-relaxed text-[#F5F0E8]/70 font-medium">
            {copy}
          </p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

function GlassCard({
  children,
  className = '',
  style,
  ...props
}: {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
  [key: string]: unknown;
}) {
  return (
    <section
      className={`glass-max relative ${className}`}
      style={{
        backgroundImage: 'radial-gradient(circle, rgba(43, 89, 255, 0.08) 1px, transparent 1px)',
        backgroundSize: '16px 16px',
        ...style,
      }}
      {...props}
    >
      {children}
    </section>
  );
}

function ProgressBar({
  value,
  color = 'linear-gradient(90deg, #FF307F, #FFD400, #2B59FF)',
}: {
  value: number;
  color?: string;
}) {
  return (
    <div
      className="h-3 overflow-hidden border-2 border-white/20 bg-[#111111]"
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
      data-testid="progress-bar"
    >
      <div
        className="h-full transition-all duration-300"
        style={{ width: `${value}%`, background: color }}
      />
    </div>
  );
}

function Modal({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[110] grid place-items-center bg-[#0A0A0A]/85 p-5 backdrop-blur-md"
          role="dialog"
          aria-modal="true"
          aria-label={title}
        >
          <motion.div
            initial={{ scale: 0.9, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.9, y: 20 }}
            className="w-full max-w-md border-4 border-[#FFD400] bg-[#0A0A0A] p-6 shadow-[0_12px_50px_rgba(255,48,127,0.4)] sm:p-7 relative"
          >
            <div className="flex items-center justify-between border-b-2 border-white/10 pb-4">
              <h2 className="font-display text-xl font-bold tracking-wide text-[#F5F0E8]">{title}</h2>
              <Wiggle>
                <button
                  type="button"
                  onClick={onClose}
                  data-testid="button-close-modal"
                  className="grid h-9 w-9 place-items-center border-2 border-[#FF307F] bg-[#111111] text-[#F5F0E8] hover:bg-[#FF307F] hover:text-[#0A0A0A] transition-colors"
                >
                  <X size={18} strokeWidth={2.5} />
                </button>
              </Wiggle>
            </div>
            <div className="pt-4">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function StatTile({
  label,
  value,
  change,
  color,
}: {
  label: string;
  value: string;
  change: string;
  color: string;
}) {
  return (
    <GlassCard
      className="p-5 border-l-8"
      style={{
        borderLeftColor: color,
        boxShadow: `0 8px 30px ${color}26`,
      }}
    >
      <div className="flex items-start justify-between">
        <span className="font-mono text-xs font-black uppercase tracking-widest text-[#F5F0E8]/70">
          {label}
        </span>
        <span
          className="h-3 w-3 shrink-0"
          style={{ background: color, boxShadow: `0 0 16px ${color}` }}
        />
      </div>
      <div
        className="mt-4 font-display text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E8]"
        data-testid={`text-stat-${label.toLowerCase().replaceAll(' ', '-')}`}
      >
        {value}
      </div>
      <div className="mt-2 flex items-center gap-1.5 text-xs font-bold text-[#00B37E]">
        <ArrowDownRight size={14} className="rotate-180" />
        <span>{change}</span>
        <span className="text-[#F5F0E8]/50 font-normal">vs last month</span>
      </div>
    </GlassCard>
  );
}

function Thumbnail({
  gradient,
  title,
  duration,
  large = false,
}: {
  gradient: string;
  title?: string;
  duration?: string;
  large?: boolean;
}) {
  return (
    <div
      className={`group relative overflow-hidden border-2 border-white/20 ${
        large ? 'aspect-[16/9]' : 'aspect-[1.46/1]'
      }`}
      style={{ background: gradient }}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_72%_22%,rgba(255,255,255,.35),transparent_25%),linear-gradient(120deg,transparent,rgba(0,0,0,.5))]" />
      <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-[#0A0A0A] to-transparent" />
      <Starburst
        text="★"
        size="30px"
        className="absolute top-2 right-2 z-10"
        color="#FFD400"
        textColor="#0A0A0A"
      />
      <div className="absolute bottom-3 left-3 right-3 flex items-end justify-between z-10">
        {title && (
          <span className="max-w-[76%] truncate font-display text-xs font-bold tracking-wide text-white drop-shadow">
            {title}
          </span>
        )}
        {duration && (
          <span className="border border-white/30 bg-[#0A0A0A]/80 px-2 py-0.5 font-mono text-[10px] font-bold text-[#FFD400]">
            {duration}
          </span>
        )}
      </div>
    </div>
  );
}

function ProjectCard({
  project,
  compact = false,
}: {
  project: (typeof projects)[number];
  compact?: boolean;
}) {
  const notify = useNotify();
  return (
    <GlassCard
      className="group overflow-hidden border-4 border-[#2B59FF]/50 hover:border-[#FF307F] transition-all hover:shadow-[0_8px_30px_rgba(255,48,127,0.35)] p-2.5"
      data-testid={`card-project-${project.id}`}
    >
      <div>
        <Thumbnail
          gradient={project.gradient}
          title={compact ? undefined : project.title}
          duration={project.duration}
        />
      </div>
      <div className="flex items-center justify-between gap-3 px-2 py-3">
        <div className="min-w-0">
          <div
            className="truncate font-display text-sm font-bold text-[#F5F0E8] group-hover:text-[#FFD400] transition-colors"
            data-testid={`text-project-title-${project.id}`}
          >
            {project.title}
          </div>
          <div className="mt-1 flex items-center gap-2 text-xs font-medium text-[#F5F0E8]/60">
            <span className="text-[#FF7A00] font-black uppercase tracking-wider text-[10px]">
              {project.style}
            </span>
            <span className="h-1.5 w-1.5 bg-[#FFD400]" />
            <span>{project.time}</span>
          </div>
        </div>
        <Wiggle>
          <button
            type="button"
            onClick={() => notify(`${project.title} opened in preview.`, 'success')}
            data-testid={`button-open-project-${project.id}`}
            className="grid h-8 w-8 shrink-0 place-items-center border-2 border-white/20 bg-[#111111] text-[#F5F0E8] opacity-80 group-hover:opacity-100 hover:border-[#FF307F] hover:bg-[#FF307F] hover:text-[#0A0A0A] transition-all"
          >
            <MoreHorizontal size={16} />
          </button>
        </Wiggle>
      </div>
    </GlassCard>
  );
}

function StepRail({
  current,
  setCurrent,
}: {
  current: number;
  setCurrent: (step: number) => void;
}) {
  const steps = ['Upload', 'Trend', 'Generate', 'Preview'];
  return (
    <div className="mb-8 flex w-full items-center overflow-x-auto pb-2 hide-scrollbar">
      {steps.map((step, i) => {
        const number = i + 1;
        const done = number < current;
        const active = number === current;
        return (
          <div key={step} className="flex min-w-[140px] flex-1 items-center">
            <Wiggle>
              <button
                type="button"
                onClick={() => (number <= current ? setCurrent(number) : undefined)}
                data-testid={`button-step-${number}`}
                className={`flex items-center gap-2.5 text-xs uppercase tracking-wider font-bold transition-all px-2 py-1 ${
                  active
                    ? 'text-[#FFD400]'
                    : done
                    ? 'text-[#00B37E]'
                    : 'text-[#F5F0E8]/40'
                }`}
              >
                <span
                  className={`grid h-8 w-8 place-items-center border-3 font-mono text-xs font-black transition-all ${
                    active
                      ? 'border-[#FFD400] bg-[#FF307F] text-[#0A0A0A] shadow-[0_4px_0_#2B59FF]'
                      : done
                      ? 'border-[#00B37E] bg-[#00B37E] text-[#0A0A0A]'
                      : 'border-white/20 bg-[#111111] text-[#F5F0E8]/40'
                  }`}
                >
                  {done ? <Check size={16} strokeWidth={3} /> : `0${number}`}
                </span>
                <span>{step}</span>
              </button>
            </Wiggle>
            {number < steps.length && (
              <span
                className={`mx-3 h-1 flex-1 border-t-2 ${
                  done
                    ? 'border-[#00B37E]'
                    : active
                    ? 'border-[#FF307F]'
                    : 'border-white/10'
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

function ReferenceStyleCard({
  style,
  selected,
  onSelect,
}: {
  style: (typeof styles)[number];
  selected: boolean;
  onSelect: () => void;
}) {
  const [referenceName, setReferenceName] = useState('');
  const notify = useNotify();
  const addReference = (file?: File) => {
    if (!file) return;
    setReferenceName(file.name);
    notify(`Reference video added to ${style.name}.`, 'success');
  };
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') onSelect();
      }}
      data-testid={`reference-style-${style.id}`}
      className={`group relative overflow-hidden text-left transition-all duration-300 hover:-translate-y-1 ${
        selected
          ? 'border-4 border-[#FFD400] cta-glow shadow-[0_8px_30px_rgba(255,212,0,0.35)]'
          : 'border-4 border-white/15 hover:border-[#FF307F]'
      }`}
    >
      <div className="relative aspect-[1.26/1]" style={{ background: style.gradient }}>
        <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(0,0,0,.1),rgba(0,0,0,.6))]" />
        <label
          onClick={(event) => event.stopPropagation()}
          className="absolute left-4 top-4 flex cursor-pointer items-center gap-1.5 border-2 border-[#FFD400] bg-[#0A0A0A] px-2.5 py-1 text-[10px] font-black uppercase tracking-wider text-[#FFD400] transition hover:bg-[#FFD400] hover:text-[#0A0A0A]"
          title="Upload your own reference video"
        >
          <input
            type="file"
            accept="video/*"
            className="hidden"
            onChange={(event) => addReference(event.target.files?.[0])}
            data-testid={`input-reference-${style.id}`}
          />
          {referenceName ? <Check size={14} className="text-[#00B37E]" /> : <UploadCloud size={14} />}
          {referenceName ? 'Added' : 'Add video'}
        </label>
        {selected && (
          <span className="absolute right-3 top-3 grid h-8 w-8 place-items-center border-2 border-[#0A0A0A] bg-[#FFD400] text-[#0A0A0A] font-black">
            <Check size={18} strokeWidth={3} />
          </span>
        )}
        <div className="absolute bottom-4 left-4 right-4">
          <div className="mb-1 text-[10px] font-black uppercase tracking-[.2em] text-[#FFD400]">
            {style.type}
          </div>
          <div className="font-display text-2xl font-bold tracking-wide text-white">
            {style.name}
          </div>
        </div>
      </div>
      <div className="border-t-2 border-white/10 bg-[#111111] p-4">
        <p className="min-h-[40px] text-xs leading-5 text-[#F5F0E8]/70">
          {referenceName ? `${referenceName} is ready as your reference.` : style.description}
        </p>
        <div className="mt-3 flex items-center justify-between text-[10px] font-black uppercase tracking-wider text-[#FF7A00]">
          <span>{referenceName ? 'Your reference' : style.tag}</span>
          <span className="font-mono text-[#F5F0E8]/50">{style.stat}</span>
        </div>
      </div>
    </div>
  );
}

function StyleCard({
  style,
  selected,
  onSelect,
}: {
  style: (typeof styles)[number];
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <Wiggle className="w-full">
      <button
        type="button"
        onClick={onSelect}
        data-testid={`button-style-${style.id}`}
        className={`group relative w-full overflow-hidden text-left transition-all duration-300 hover:-translate-y-1 ${
          selected
            ? 'border-4 border-[#FFD400] cta-glow shadow-[0_8px_30px_rgba(255,212,0,0.35)]'
            : 'border-4 border-white/15 hover:border-[#FF307F]'
        }`}
      >
        <div className="relative aspect-[1.26/1]" style={{ background: style.gradient }}>
          <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(0,0,0,.1),rgba(0,0,0,.6))]" />
          <div className="absolute left-4 top-4 flex h-9 w-9 items-center justify-center border-2 border-[#FFD400] bg-[#FF307F] font-headline text-xs font-bold text-[#0A0A0A] shadow-[0_3px_0_#2B59FF]">
            {style.icon}
          </div>
          {selected && (
            <span className="absolute right-3 top-3 grid h-8 w-8 place-items-center border-2 border-[#0A0A0A] bg-[#FFD400] text-[#0A0A0A] font-black">
              <Check size={18} strokeWidth={3} />
            </span>
          )}
          <div className="absolute bottom-4 left-4 right-4">
            <div className="mb-1 text-[10px] font-black uppercase tracking-[.2em] text-[#FFD400]">
              {style.type}
            </div>
            <div className="font-display text-2xl font-bold tracking-wide text-white">
              {style.name}
            </div>
          </div>
        </div>
        <div className="border-t-2 border-white/10 bg-[#111111] p-4">
          <p className="min-h-[40px] text-xs leading-5 text-[#F5F0E8]/70">{style.description}</p>
          <div className="mt-3 flex items-center justify-between text-[10px] font-black uppercase tracking-wider text-[#FF7A00]">
            <span>{style.tag}</span>
            <span className="font-mono text-[#F5F0E8]/50">{style.stat}</span>
          </div>
        </div>
      </button>
    </Wiggle>
  );
}

function UploadDropzone({
  fileName,
  setFileName,
  progress,
  setProgress,
}: {
  fileName: string;
  setFileName: (name: string) => void;
  progress: number;
  setProgress: (value: number) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const notify = useNotify();
  const acceptFile = (file?: File) => {
    if (!file) return;
    setFileName(file.name);
    setProgress(0);
    notify(`Uploading ${file.name}`, 'info');
  };
  useEffect(() => {
    if (!fileName || progress >= 100) return;
    const timer = window.setInterval(() => setProgress(Math.min(100, progress + 20)), 260);
    return () => window.clearInterval(timer);
  }, [fileName, progress, setProgress]);

  return (
    <div
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        acceptFile(e.dataTransfer.files[0]);
      }}
      data-testid="dropzone-raw-footage"
      onClick={() => inputRef.current?.click()}
      className="group relative flex min-h-[320px] cursor-pointer flex-col items-center justify-center overflow-hidden border-4 border-dashed border-[#FF307F]/60 bg-[#0A0A0A] pattern-checkerboard p-8 text-center transition-all hover:border-[#FFD400] hover:bg-[#FF307F]/5"
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        className="hidden"
        onChange={(e) => acceptFile(e.target.files?.[0])}
        data-testid="input-footage-file"
      />
      <div className="relative grid h-20 w-20 place-items-center border-4 border-[#FFD400] bg-[#FF307F] text-[#0A0A0A] shadow-[0_6px_0_#2B59FF] transition-transform group-hover:scale-105">
        <UploadCloud size={36} strokeWidth={2.5} />
      </div>
      <h3 className="mt-5 font-display text-xl font-bold tracking-wide text-[#F5F0E8]">
        {fileName ? fileName : 'DROP RAW FOOTAGE HERE'}
      </h3>
      <p className="mt-2 text-xs font-medium text-[#F5F0E8]/70">
        {fileName
          ? `${progress}% uploaded · MP4 · READY FOR A CUT`
          : 'or click to browse from your machine'}
      </p>
      {fileName ? (
        <div className="mt-6 w-full max-w-[320px]">
          <ProgressBar value={progress} />
          <div className="mt-2 flex justify-between font-mono text-[10px] font-bold uppercase text-[#FFD400]">
            <span>{progress === 100 ? 'UPLOAD COMPLETE' : 'UPLOADING…'}</span>
            <span>
              {progress === 100 ? '04:18' : `${Math.max(1, Math.round(progress * 0.042))} MB / 42 MB`}
            </span>
          </div>
        </div>
      ) : (
        <div className="mt-6 flex gap-3 font-mono text-[10px] font-bold uppercase tracking-widest text-[#FF7A00]">
          <span>MP4</span>
          <span>•</span>
          <span>MOV</span>
          <span>•</span>
          <span>UP TO 2GB</span>
        </div>
      )}
    </div>
  );
}

function ChatAssistant() {
  const [messages, setMessages] = useState([
    { from: 'ai', text: 'Tell me what this edit should feel like. I can shape the rhythm around it.' },
  ]);
  const [input, setInput] = useState('');
  const notify = useNotify();
  const send = () => {
    if (!input.trim()) return;
    const value = input.trim();
    setMessages((m) => [
      ...m,
      { from: 'you', text: value },
      {
        from: 'ai',
        text: value.toLowerCase().includes('faster')
          ? 'Got it — I’ll tighten the pauses and let the beat lead.'
          : 'I hear the direction. I’ll keep the texture, then make the hook arrive sooner.',
      },
    ]);
    setInput('');
    notify('AI direction added to your edit.', 'success');
  };
  return (
    <div className="flex min-h-[380px] flex-col overflow-hidden border-4 border-[#2B59FF] bg-[#0A0A0A] shadow-[0_8px_30px_rgba(43,89,255,0.25)]">
      <div className="flex items-center justify-between border-b-2 border-white/10 bg-[#111111] px-5 py-3.5">
        <div className="flex items-center gap-3">
          <span className="grid h-8 w-8 place-items-center border-2 border-[#FFD400] bg-[#2B59FF] text-[#F5F0E8] font-bold">
            <WandSparkles size={16} />
          </span>
          <div>
            <div className="font-display text-sm font-bold tracking-wide text-[#F5F0E8]">
              CUTROOM AI
            </div>
            <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-[#00B37E]">
              <span className="h-2 w-2 bg-[#00B37E] pulse-dot" />
              LISTENING
            </div>
          </div>
        </div>
        <Wiggle>
          <button
            type="button"
            onClick={() =>
              setMessages([
                {
                  from: 'ai',
                  text: 'Tell me what this edit should feel like. I can shape the rhythm around it.',
                },
              ])
            }
            data-testid="button-reset-chat"
            className="grid h-8 w-8 place-items-center border border-white/20 text-[#F5F0E8]/70 hover:border-[#FFD400] hover:text-[#FFD400] transition-colors"
          >
            <RotateCcw size={14} />
          </button>
        </Wiggle>
      </div>
      <div className="hide-scrollbar flex-1 space-y-3 overflow-y-auto p-5">
        {messages.map((message, index) => (
          <div
            key={`${message.text}-${index}`}
            className={`flex ${message.from === 'you' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] border-2 px-3.5 py-2.5 text-xs leading-relaxed ${
                message.from === 'you'
                  ? 'border-[#FF307F] bg-[#FF307F]/15 text-[#F5F0E8]'
                  : 'border-[#2B59FF] bg-[#2B59FF]/15 text-[#F5F0E8]'
              }`}
              data-testid={`chat-message-${index}`}
            >
              <div className="text-[9px] font-mono font-bold uppercase tracking-widest mb-1 text-[#FFD400]">
                {message.from === 'you' ? 'YOU' : 'STYLECUT AI'}
              </div>
              {message.text}
            </div>
          </div>
        ))}
      </div>
      <div className="border-t-2 border-white/10 bg-[#111111] p-3">
        <div className="flex items-center gap-2 border-2 border-[#FFD400] bg-[#0A0A0A] px-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            placeholder="Try “make it faster”"
            data-testid="input-chat"
            className="min-w-0 flex-1 bg-transparent py-2.5 text-xs text-[#F5F0E8] outline-none placeholder:text-[#F5F0E8]/40"
          />
          <Wiggle>
            <button
              type="button"
              onClick={send}
              data-testid="button-send-chat"
              className="border-l-2 border-[#FFD400] pl-3 py-2 text-[#FF307F] hover:text-[#FFD400] transition-colors"
            >
              <Send size={16} />
            </button>
          </Wiggle>
        </div>
      </div>
    </div>
  );
}

function Toggle({
  label,
  copy,
  value,
  onChange,
}: {
  label: string;
  copy?: string;
  value: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-4">
      <div>
        <div className="font-display text-sm font-bold tracking-wide text-[#F5F0E8]">{label}</div>
        {copy && <div className="mt-1 text-xs text-[#F5F0E8]/60">{copy}</div>}
      </div>
      <Wiggle>
        <button
          type="button"
          role="switch"
          aria-checked={value}
          onClick={() => onChange(!value)}
          data-testid={`toggle-${label.toLowerCase().replaceAll(' ', '-')}`}
          className={`relative h-7 w-14 shrink-0 border-2 border-white/20 p-1 transition-colors ${
            value ? 'bg-[#FF307F]' : 'bg-[#F5F0E8]/10'
          }`}
        >
          <span
            className={`block h-4 w-5 bg-[#FFD400] border border-[#0A0A0A] shadow transition-transform ${
              value ? 'translate-x-6' : 'translate-x-0'
            }`}
          />
        </button>
      </Wiggle>
    </div>
  );
}

function Dashboard() {
  const notify = useNotify();
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <PageTitle
        eyebrow="TUESDAY, MARCH 26 // STUDIO ARCHIVE"
        title={
          <div className="space-y-1">
            <span className="block font-headline text-[clamp(2rem,5vw,3.5rem)] text-[#F5F0E8] tracking-widest leading-none -rotate-1 inline-block">
              MAKE THE MOMENT
            </span>
            <br />
            <span className="block font-headline text-[clamp(3rem,8vw,6rem)] text-outline tracking-wider leading-none -rotate-2 inline-block">
              IMPOSSIBLE
            </span>
            <br />
            <span className="font-display text-[clamp(2rem,5.5vw,4.5rem)] text-gradient-max rotate-1 inline-block">
              TO SCROLL PAST.
            </span>
          </div>
        }
        copy="Your studio is electric, your raw footage is loaded. Pick up where you left off or give a new cut its first heartbeat."
        action={
          <Wiggle>
            <Link
              href="/create"
              data-testid="link-start-edit"
              className="group inline-flex items-center justify-center gap-2.5 bg-[#FF307F] px-6 py-4 font-display text-sm font-bold uppercase tracking-wider text-[#0A0A0A] border-4 border-[#FFD400] shadow-[0_6px_0_#2B59FF] hover:-translate-y-1 active:translate-y-0 active:shadow-none transition-all cta-glow"
            >
              Start a new edit{' '}
              <ArrowRight
                size={18}
                strokeWidth={2.5}
                className="transition group-hover:translate-x-1"
              />
            </Link>
          </Wiggle>
        }
      />

      <div className="relative grid gap-5 xl:grid-cols-[1.55fr_.85fr]">
        <Sticker emoji="🔥" className="-top-5 -right-3" rotate={15} size="3rem" />
        <GlassCard className="relative min-h-[340px] overflow-hidden p-6 sm:p-8 border-4 border-[#FF307F] shadow-[0_12px_40px_rgba(255,48,127,0.25)] pattern-checkerboard">
          <div className="relative z-10 max-w-[420px]">
            <div className="flex items-center gap-2 font-mono text-[11px] font-black uppercase tracking-[.25em] text-[#FFD400]">
              <span className="h-2 w-2 bg-[#00B37E] pulse-dot" />
              Edit in progress
            </div>
            <h2 className="mt-5 font-display text-3xl sm:text-4xl font-bold leading-tight tracking-tight text-[#F5F0E8]">
              The city is still{' '}
              <span className="font-headline text-3xl sm:text-4xl text-[#FFD400] block mt-1">
                AWAKE.
              </span>
            </h2>
            <p className="mt-3 max-w-[320px] text-xs leading-relaxed text-[#F5F0E8]/70">
              We found 14 kinetic moments with an electric pulse. Your first pass is assembled and ready.
            </p>
            <div className="mt-7 flex items-center gap-3">
              <Wiggle>
                <Link
                  href="/create"
                  data-testid="link-continue-edit"
                  className="inline-flex items-center gap-2 border-3 border-[#0A0A0A] bg-[#FFD400] px-5 py-3 font-display text-xs font-bold text-[#0A0A0A] shadow-[0_4px_0_#FF307F] hover:bg-white transition-all uppercase tracking-wider"
                >
                  Continue editing <ArrowRight size={15} />
                </Link>
              </Wiggle>
              <Wiggle>
                <button
                  type="button"
                  onClick={() => notify('Preview opened in cinema mode.', 'success')}
                  data-testid="button-preview-edit"
                  className="grid h-11 w-11 place-items-center border-3 border-white/20 bg-[#111111] text-[#F5F0E8] hover:border-[#FF307F] hover:bg-[#FF307F] hover:text-[#0A0A0A] transition-all"
                >
                  <Play size={16} fill="currentColor" />
                </button>
              </Wiggle>
            </div>
          </div>

          <div className="absolute bottom-[-24px] right-[-10px] hidden h-[270px] w-[44%] rotate-[-6deg] border-4 border-[#FFD400] bg-[linear-gradient(135deg,#0A0A0A,#FF307F_50%,#2B59FF)] shadow-[0_25px_80px_rgba(0,0,0,.7)] sm:block">
            <div className="absolute inset-3 border-2 border-white/20 bg-[radial-gradient(circle_at_64%_27%,rgba(255,255,255,.6),transparent_10%),linear-gradient(130deg,transparent,rgba(0,0,0,.6))]" />
            <Starburst
              text="HOT"
              size="56px"
              className="absolute -top-6 -right-6 z-20"
              color="#FFD400"
              textColor="#0A0A0A"
            />
            <div className="absolute bottom-4 left-4 flex items-center gap-2 font-mono text-[11px] font-bold text-white drop-shadow">
              <span className="h-2 w-2 bg-[#00B37E]" />
              00:24 / 00:42
            </div>
          </div>

          <div className="absolute bottom-5 left-6 right-6 sm:left-8 sm:right-8">
            <div className="mb-2 flex justify-between font-mono text-xs font-bold uppercase text-[#F5F0E8]/70">
              <span>AI Assembly</span>
              <span className="text-[#FFD400]">68%</span>
            </div>
            <div className="h-2 overflow-hidden border border-white/20 bg-[#111111]">
              <div className="relative h-full w-[68%] overflow-hidden bg-[linear-gradient(90deg,#FF307F,#FFD400,#2B59FF)]">
                <div className="sweep absolute inset-y-0 left-0 w-16 bg-white/60 blur-sm" />
              </div>
            </div>
          </div>
        </GlassCard>

        <div className="grid grid-cols-2 gap-4">
          <StatTile label="Edits completed" value="27" change="+8.4%" color="#FF307F" />
          <StatTile label="Time saved" value="4h 18m" change="+21.7%" color="#FFD400" />
          <StatTile label="Avg. retention" value="71.8%" change="+6.2%" color="#2B59FF" />
          <GlassCard className="col-span-2 flex items-center justify-between p-5 border-l-8 border-[#00B37E]">
            <div>
              <div className="font-mono text-xs font-black uppercase tracking-widest text-[#F5F0E8]/70">
                Creative Energy
              </div>
              <div className="mt-2 font-display text-2xl font-bold tracking-tight text-[#F5F0E8]">
                You are on a run.
              </div>
              <div className="mt-1 font-mono text-xs font-bold text-[#FF7A00]">
                5 edits in the last 7 days
              </div>
            </div>
            <div className="relative h-16 w-32 border-2 border-[#00B37E]/40 bg-[#111111] p-1">
              <div
                className="h-full w-full opacity-80"
                style={{
                  background:
                    'linear-gradient(135deg, transparent 0 5%, #FF307F 5% 7%, transparent 7% 15%, #FFD400 15% 17%, transparent 17% 26%, #2B59FF 26% 28%, transparent 28% 36%, #FF307F 36% 38%, transparent 38% 48%, #FFD400 48% 50%, transparent 50% 61%, #2B59FF 61% 63%, transparent 63% 75%, #FF307F 75% 77%, transparent 77%)',
                  clipPath:
                    'polygon(0 85%, 5% 50%, 10% 80%, 16% 33%, 22% 74%, 28% 20%, 34% 60%, 40% 37%, 46% 70%, 52% 15%, 58% 55%, 64% 32%, 70% 62%, 76% 8%, 82% 48%, 88% 25%, 94% 65%, 100% 10%, 100% 100%, 0 100%)',
                }}
              />
            </div>
          </GlassCard>
        </div>
      </div>

      <div className="mt-12 flex items-end justify-between">
        <div>
          <div className="font-mono text-xs font-black uppercase tracking-[.25em] text-[#FF7A00]">
            Keep Going
          </div>
          <h2 className="mt-2 font-display text-2xl sm:text-3xl font-bold tracking-tight text-[#F5F0E8]">
            Recent projects
          </h2>
        </div>
        <Wiggle>
          <Link
            href="/projects"
            data-testid="link-view-projects"
            className="text-xs font-bold uppercase tracking-wider text-[#FFD400] hover:text-[#FF307F] transition-colors"
          >
            View all <ArrowRight size={14} className="ml-1 inline" />
          </Link>
        </Wiggle>
      </div>

      <div className="mt-5 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {projects.map((project, i) => (
          <motion.div
            key={project.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: i * 0.1 }}
          >
            <ProjectCard project={project} />
          </motion.div>
        ))}
      </div>

      <GlassCard className="mt-10 flex flex-col gap-5 p-6 border-4 border-[#00B37E] sm:flex-row sm:items-center sm:justify-between shadow-[0_8px_30px_rgba(0,179,126,0.25)]">
        <div className="flex items-center gap-4">
          <div className="grid h-12 w-12 place-items-center border-3 border-[#FFD400] bg-[#00B37E] text-[#0A0A0A] font-black">
            <WandSparkles size={24} />
          </div>
          <div>
            <div className="font-display text-base font-bold text-[#F5F0E8]">
              A style for your next chapter
            </div>
            <div className="mt-1 text-xs text-[#F5F0E8]/70">
              Based on your last 3 edits, Quiet Luxury might be your next signature language.
            </div>
          </div>
        </div>
        <Wiggle>
          <Link
            href="/styles"
            data-testid="link-explore-recommendation"
            className="inline-flex items-center gap-2 border-4 border-[#FF307F] bg-[#FFD400] px-5 py-3 font-display text-xs font-bold text-[#0A0A0A] uppercase tracking-wider hover:bg-white transition-all shadow-[0_4px_0_#2B59FF]"
          >
            Explore style <ArrowRight size={14} className="ml-1 inline" />
          </Link>
        </Wiggle>
      </GlassCard>
    </motion.div>
  );
}

function CreatePage() {
  const notify = useNotify();
  const [stage, setStage] = useState(1);
  const [fileName, setFileName] = useState('');
  const [progress, setProgress] = useState(0);
  const [selectedStyle, setSelectedStyle] = useState(styles[0]);
  const [intensity, setIntensity] = useState(72);
  const [pace, setPace] = useState('Balanced');
  const [generating, setGenerating] = useState(false);

  const goNext = () => {
    if (stage === 1 && (!fileName || progress < 100)) {
      notify('Add a complete upload before choosing a style.', 'info');
      return;
    }
    if (stage < 5) setStage(stage + 1);
  };

  const generate = () => {
    setGenerating(true);
    setStage(4);
    notify('StyleCut is finding the rhythm in your footage.', 'info');
    window.setTimeout(() => {
      setGenerating(false);
      setStage(5);
      notify('Your first cut is ready to preview.', 'success');
    }, 2800);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <PageTitle
        eyebrow="CREATE STUDIO // LOCAL WORKSPACE"
        title={
          <div>
            <span className="block font-headline text-[clamp(2rem,5vw,3.5rem)] text-[#F5F0E8] tracking-widest leading-none -rotate-1 inline-block">
              TURN RAW FOOTAGE
            </span>
            <br />
            <span className="font-display text-[clamp(2.5rem,6vw,5rem)] text-gradient-max rotate-1 inline-block">
              INTO A POINT OF VIEW.
            </span>
          </div>
        }
        copy="Five deliberate steps. One uncompromising edit that sounds and hits like you."
        action={
          <div className="flex items-center gap-2 border-2 border-white/20 bg-[#111111] px-3.5 py-2 font-mono text-xs font-bold uppercase tracking-wider text-[#FFD400]">
            <LockKeyhole size={14} /> Local demo workspace
          </div>
        }
      />

      <StepRail current={stage} setCurrent={setStage} />

      {stage === 1 && (
        <div className="grid gap-6 xl:grid-cols-[1.4fr_.6fr]">
          <GlassCard className="p-6 sm:p-8 border-4 border-[#FF307F] shadow-[0_12px_40px_rgba(255,48,127,0.3)]">
            <div className="mb-6 flex items-start justify-between">
              <div>
                <h2 className="font-display text-2xl font-bold tracking-wide text-[#F5F0E8]">
                  Upload raw footage
                </h2>
                <p className="mt-1 text-xs text-[#F5F0E8]/70">
                  Start with the uncut version. We’ll extract the rhythm and moments inside.
                </p>
              </div>
              <span className="border-2 border-[#FFD400] bg-[#FF307F] px-2.5 py-1 font-mono text-xs font-black text-[#0A0A0A]">
                01 / 05
              </span>
            </div>
            <UploadDropzone
              fileName={fileName}
              setFileName={setFileName}
              progress={progress}
              setProgress={setProgress}
            />
            <div className="mt-6 flex justify-end">
              <Wiggle>
                <button
                  type="button"
                  onClick={goNext}
                  data-testid="button-next-style"
                  className="inline-flex items-center gap-2 bg-[#FF307F] px-6 py-3.5 font-display text-xs font-bold uppercase tracking-wider text-[#0A0A0A] border-4 border-[#FFD400] shadow-[0_6px_0_#2B59FF] hover:-translate-y-1 active:translate-y-0 active:shadow-none transition-all cta-glow"
                >
                  Choose a style <ArrowRight size={16} />
                </button>
              </Wiggle>
            </div>
          </GlassCard>

          <div className="relative">
            <Sticker emoji="⚡" className="-top-4 -right-3" rotate={12} size="2.75rem" />
            <GlassCard className="p-6 sm:p-8 border-4 border-[#2B59FF] bg-[#0A0A0A] shadow-[0_8px_30px_rgba(43,89,255,0.2)]">
              <div className="flex items-center gap-2 font-mono text-xs font-black uppercase tracking-[.25em] text-[#FFD400]">
                <Gauge size={16} /> Good to know
              </div>
              <div className="mt-6 space-y-6">
                {[
                  ['01', 'KEEP IT HONEST', 'Long, unpolished takes give the AI maximum texture to work with.'],
                  ['02', 'SOUND MATTERS', 'Clean ambient audio helps us pinpoint cut points that feel human.'],
                  ['03', 'VERTICAL WINS', 'We frame the final output for 9:16 vertical reels by default.'],
                ].map(([number, title, copy]) => (
                  <div key={number} className="border-2 border-white/10 bg-[#111111] p-4 flex gap-3.5">
                    <span className="font-mono text-sm font-black text-[#FF307F]">{number}</span>
                    <div>
                      <div className="font-display text-sm font-bold text-[#F5F0E8]">{title}</div>
                      <p className="mt-1 text-xs leading-relaxed text-[#F5F0E8]/70">{copy}</p>
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>
        </div>
      )}

      {stage === 2 && (
        <div>
          <div className="mb-6 flex items-center justify-between border-b-2 border-white/10 pb-4">
            <div>
              <h2 className="font-display text-2xl font-bold tracking-wide text-[#F5F0E8]">
                Choose a visual language
              </h2>
              <p className="mt-1 font-mono text-xs text-[#FFD400]">
                {fileName || 'Your footage'} · 04:18 · 42 MB
              </p>
            </div>
            <Wiggle>
              <button
                type="button"
                onClick={() => setStage(1)}
                data-testid="button-back-upload"
                className="border-3 border-[#F5F0E8]/30 px-4 py-2 font-display text-xs font-bold uppercase tracking-wider text-[#F5F0E8] hover:bg-[#FF307F] hover:text-[#0A0A0A] transition-colors"
              >
                Back to upload
              </button>
            </Wiggle>
          </div>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {styles.map((style) => (
              <StyleCard
                key={style.id}
                style={style}
                selected={selectedStyle.id === style.id}
                onSelect={() => setSelectedStyle(style)}
              />
            ))}
          </div>
          <div className="mt-8 flex justify-end">
            <Wiggle>
              <button
                type="button"
                onClick={goNext}
                data-testid="button-next-customize"
                className="inline-flex items-center gap-2 bg-[#FF307F] px-6 py-3.5 font-display text-xs font-bold uppercase tracking-wider text-[#0A0A0A] border-4 border-[#FFD400] shadow-[0_6px_0_#2B59FF] hover:-translate-y-1 active:translate-y-0 active:shadow-none transition-all cta-glow"
              >
                Customize with AI <ArrowRight size={16} />
              </button>
            </Wiggle>
          </div>
        </div>
      )}

      {stage === 3 && (
        <div className="grid gap-6 xl:grid-cols-[1fr_390px]">
          <GlassCard className="p-6 sm:p-8 border-4 border-[#FF307F] shadow-[0_12px_40px_rgba(255,48,127,0.3)]">
            <div className="mb-7 flex items-start justify-between border-b-2 border-white/10 pb-4">
              <div>
                <h2 className="font-display text-2xl font-bold tracking-wide text-[#F5F0E8]">
                  Customize with AI
                </h2>
                <p className="mt-1 text-xs text-[#F5F0E8]/70">
                  Shape the kinetic edit without stripping the authentic accidents.
                </p>
              </div>
              <span className="border-2 border-[#FFD400] bg-[#FF307F] px-3 py-1 font-display text-xs font-bold text-[#0A0A0A] uppercase tracking-wider">
                {selectedStyle.name}
              </span>
            </div>

            <div className="space-y-8">
              <div>
                <div className="flex items-center justify-between">
                  <label className="font-display text-sm font-bold uppercase tracking-wide text-[#F5F0E8]">
                    Style intensity
                  </label>
                  <span className="font-mono text-sm font-black text-[#FFD400]">{intensity}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={intensity}
                  onChange={(e) => setIntensity(Number(e.target.value))}
                  data-testid="input-style-intensity"
                  className="mt-4 w-full accent-[#FF307F] cursor-pointer h-3 bg-[#111111] border-2 border-white/20"
                />
                <div className="mt-2 flex justify-between font-mono text-[10px] font-bold uppercase text-[#F5F0E8]/50">
                  <span>Subtle</span>
                  <span>Signature</span>
                  <span>Unmistakable</span>
                </div>
              </div>

              <div>
                <div className="font-display text-sm font-bold uppercase tracking-wide text-[#F5F0E8]">
                  Cutting pace
                </div>
                <div className="mt-3 grid grid-cols-3 gap-3">
                  {['Slow burn', 'Balanced', 'Kinetic'].map((option) => (
                    <Wiggle key={option} className="w-full">
                      <button
                        type="button"
                        onClick={() => setPace(option)}
                        data-testid={`button-pace-${option.toLowerCase().replaceAll(' ', '-')}`}
                        className={`w-full border-3 px-3 py-3.5 font-display text-xs font-bold uppercase tracking-wider transition-all ${
                          pace === option
                            ? 'border-[#FFD400] bg-[#FF307F] text-[#0A0A0A] shadow-[0_4px_0_#2B59FF]'
                            : 'border-white/20 bg-[#111111] text-[#F5F0E8]/70 hover:border-[#FFD400]'
                        }`}
                      >
                        {option}
                      </button>
                    </Wiggle>
                  ))}
                </div>
              </div>

              <div>
                <div className="font-display text-sm font-bold uppercase tracking-wide text-[#F5F0E8]">
                  Keep the good stuff
                </div>
                <div className="mt-3 divide-y-2 divide-white/10 border-2 border-white/15 bg-[#111111] px-4">
                  <Toggle
                    label="Natural pauses"
                    copy="Leave room for breath between the spoken lines."
                    value={true}
                    onChange={() => notify('Natural pauses preference updated.', 'success')}
                  />
                  <Toggle
                    label="Original audio"
                    copy="Keep source environmental audio under the beat bed."
                    value={true}
                    onChange={() => notify('Original audio preference updated.', 'success')}
                  />
                  <Toggle
                    label="Auto captions"
                    copy="Make every word hit hard, even on mute."
                    value={false}
                    onChange={() => notify('Auto captions preference updated.', 'success')}
                  />
                </div>
              </div>
            </div>

            <div className="mt-8 flex justify-end">
              <Wiggle>
                <button
                  type="button"
                  onClick={generate}
                  data-testid="button-generate-edit"
                  className="group inline-flex items-center gap-2 bg-[#FF307F] px-6 py-4 font-display text-xs font-bold uppercase tracking-wider text-[#0A0A0A] border-4 border-[#FFD400] shadow-[0_6px_0_#2B59FF] hover:-translate-y-1 active:translate-y-0 active:shadow-none transition-all cta-glow"
                >
                  Generate my edit{' '}
                  <Sparkles size={16} className="transition group-hover:rotate-12" />
                </button>
              </Wiggle>
            </div>
          </GlassCard>

          <ChatAssistant />
        </div>
      )}

      {stage === 4 && (
        <GlassCard className="relative min-h-[520px] overflow-hidden p-6 sm:p-12 border-4 border-[#2B59FF] shadow-[0_12px_50px_rgba(43,89,255,0.35)] pattern-checkerboard">
          <Sticker emoji="⚡" className="top-8 right-12" rotate={14} size="3.5rem" />
          <Sticker emoji="✨" className="bottom-12 left-12" rotate={-10} size="3rem" />
          <div className="relative z-10 mx-auto flex max-w-lg flex-col items-center text-center">
            <div className="relative grid h-28 w-28 place-items-center border-4 border-[#FFD400] bg-[#FF307F] text-[#0A0A0A] shadow-[0_0_60px_rgba(255,48,127,0.5)]">
              <WandSparkles size={40} strokeWidth={2} />
            </div>
            <div className="mt-8 font-mono text-xs font-black uppercase tracking-[.3em] text-[#FFD400]">
              {generating ? 'Building your first cut' : 'Generation complete'}
            </div>
            <h2 className="mt-3 font-display text-3xl sm:text-4xl font-bold tracking-tight text-[#F5F0E8]">
              {generating ? 'FINDING THE PULSE.' : 'YOUR CUT IS READY.'}
            </h2>
            <p className="mt-3 text-xs leading-relaxed text-[#F5F0E8]/70">
              {generating
                ? 'Scanning raw footage for motion spikes, micro-reactions, and the rhythm of the track.'
                : 'We found the narrative thread. Take a full look, then lock it down.'}
            </p>

            {generating ? (
              <div className="mt-10 w-full">
                <div className="mb-2 flex justify-between font-mono text-xs font-black uppercase text-[#F5F0E8]/70">
                  <span>Assembling moments</span>
                  <span className="text-[#FFD400]">LIVE</span>
                </div>
                <div className="h-3 overflow-hidden border-2 border-white/20 bg-[#111111]">
                  <div className="sweep h-full w-full bg-[linear-gradient(90deg,#FF307F,#FFD400,#2B59FF)]" />
                </div>
                <div className="mt-8 grid grid-cols-3 gap-3">
                  {['Reading 84 clips', 'Mapping the beat', 'Balancing color'].map((item, i) => (
                    <div
                      key={item}
                      className="border-2 border-[#2B59FF]/50 bg-[#111111] p-3 text-xs font-bold uppercase text-[#F5F0E8]"
                    >
                      <span className="mb-1 block font-mono text-[10px] text-[#FFD400]">
                        0{i + 1}
                      </span>
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <Wiggle>
                <button
                  type="button"
                  onClick={() => setStage(5)}
                  data-testid="button-open-result"
                  className="mt-8 inline-flex items-center gap-2 bg-[#FF307F] px-6 py-3.5 font-display text-xs font-bold uppercase tracking-wider text-[#0A0A0A] border-4 border-[#FFD400] shadow-[0_6px_0_#2B59FF] hover:-translate-y-1 active:translate-y-0 active:shadow-none transition-all cta-glow"
                >
                  Preview result <ArrowRight size={16} />
                </button>
              </Wiggle>
            )}
          </div>
        </GlassCard>
      )}

      {stage === 5 && (
        <div className="grid gap-6 xl:grid-cols-[1.18fr_.82fr]">
          <GlassCard className="overflow-hidden p-4 sm:p-6 border-4 border-[#FF307F] shadow-[0_12px_40px_rgba(255,48,127,0.3)]">
            <div className="relative aspect-[9/12] max-h-[600px] overflow-hidden border-4 border-[#FFD400] bg-[linear-gradient(140deg,#0A0A0A,#FF307F_50%,#2B59FF)]">
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_68%_26%,rgba(255,255,255,.5),transparent_20%),linear-gradient(130deg,transparent,rgba(0,0,0,.6))]" />
              <div className="absolute left-5 top-5 border-2 border-white/30 bg-[#0A0A0A]/80 px-2.5 py-1 font-mono text-[10px] font-bold text-[#FFD400]">
                STYLECUT / 01
              </div>
              <Wiggle>
                <button
                  type="button"
                  onClick={() => notify('Cinema mode opened.', 'success')}
                  data-testid="button-play-result"
                  className="absolute left-1/2 top-1/2 grid h-20 w-20 -translate-x-1/2 -translate-y-1/2 place-items-center border-4 border-[#FFD400] bg-[#FF307F] text-[#0A0A0A] shadow-[0_0_35px_rgba(255,48,127,0.6)] transition hover:scale-105"
                >
                  <Play size={26} fill="currentColor" />
                </button>
              </Wiggle>
              <div className="absolute inset-x-5 bottom-5">
                <div className="mb-2 text-right font-mono text-xs font-bold text-white drop-shadow">
                  00:42 / 00:42
                </div>
                <div className="h-2 overflow-hidden border border-white/30 bg-black/40">
                  <div className="h-full w-full bg-[#FFD400]" />
                </div>
                <div className="mt-3 flex items-center justify-between font-mono text-xs font-bold text-white drop-shadow">
                  <span>Neon Noir / first pass</span>
                  <span className="flex items-center gap-1.5">
                    <Volume2 size={14} /> 84%
                  </span>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 px-1 pt-5">
              <div>
                <div className="font-display text-base font-bold text-[#F5F0E8]">
                  The city is still awake
                </div>
                <div className="mt-1 font-mono text-xs text-[#FFD400]">
                  First pass · 9:16 · 1080 × 1920
                </div>
              </div>
              <div className="flex gap-2.5">
                <Wiggle>
                  <button
                    type="button"
                    onClick={() => notify('Download queued for your local demo.', 'success')}
                    data-testid="button-download-result"
                    className="grid h-10 w-10 place-items-center border-2 border-white/20 bg-[#111111] text-[#F5F0E8] hover:border-[#FFD400] hover:text-[#FFD400] transition-colors"
                  >
                    <Download size={18} />
                  </button>
                </Wiggle>
                <Wiggle>
                  <button
                    type="button"
                    onClick={() => notify('Share link copied to clipboard.', 'success')}
                    data-testid="button-share-result"
                    className="grid h-10 w-10 place-items-center border-2 border-white/20 bg-[#111111] text-[#F5F0E8] hover:border-[#FFD400] hover:text-[#FFD400] transition-colors"
                  >
                    <Share2 size={18} />
                  </button>
                </Wiggle>
              </div>
            </div>
          </GlassCard>

          <div className="space-y-6">
            <GlassCard className="p-6 border-4 border-[#2B59FF] shadow-[0_8px_30px_rgba(43,89,255,0.2)]">
              <div className="flex items-center justify-between border-b-2 border-white/10 pb-3">
                <h2 className="font-display text-base font-bold text-[#F5F0E8]">Before / After</h2>
                <Eye size={18} className="text-[#FFD400]" />
              </div>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <div>
                  <div className="aspect-[9/12] border-2 border-white/20 bg-[linear-gradient(145deg,#222,#444)]" />
                  <div className="mt-2 font-mono text-[10px] font-black uppercase tracking-wider text-[#F5F0E8]/50">
                    Raw
                  </div>
                </div>
                <div>
                  <div className="aspect-[9/12] border-2 border-[#FFD400] bg-[linear-gradient(145deg,#0A0A0A,#FF307F_50%,#2B59FF)] shadow-[0_4px_16px_rgba(255,48,127,0.3)]" />
                  <div className="mt-2 font-mono text-[10px] font-black uppercase tracking-wider text-[#FFD400]">
                    Stylecut
                  </div>
                </div>
              </div>
              <div className="mt-6 space-y-3">
                {[
                  ['Scored moments', '14 / 84 clips'],
                  ['Captions', 'Ready'],
                  ['Color language', selectedStyle.name],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    className="flex items-center justify-between border-t border-white/10 pt-3 font-mono text-xs"
                  >
                    <span className="text-[#F5F0E8]/60">{label}</span>
                    <span className="font-bold text-[#FFD400]">{value}</span>
                  </div>
                ))}
              </div>
            </GlassCard>

            <GlassCard className="p-6 border-4 border-[#FFD400] shadow-[0_8px_30px_rgba(255,212,0,0.25)]">
              <div className="flex items-center gap-2 font-display text-sm font-bold text-[#F5F0E8]">
                <Sparkles size={16} className="text-[#FF307F]" /> MAKE IT YOURS
              </div>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <Wiggle className="w-full">
                  <button
                    type="button"
                    onClick={() => setStage(3)}
                    data-testid="button-adjust-result"
                    className="w-full border-3 border-[#F5F0E8]/30 px-3 py-3 font-display text-xs font-bold uppercase tracking-wider text-[#F5F0E8] hover:bg-[#FF307F] hover:text-[#0A0A0A] transition-colors"
                  >
                    Adjust direction
                  </button>
                </Wiggle>
                <Wiggle className="w-full">
                  <button
                    type="button"
                    onClick={() => notify('Version 01 saved to Projects.', 'success')}
                    data-testid="button-save-result"
                    className="w-full border-3 border-[#FFD400] bg-[#FF307F] px-3 py-3 font-display text-xs font-bold uppercase tracking-wider text-[#0A0A0A] shadow-[0_4px_0_#2B59FF] hover:bg-[#FFD400] transition-colors"
                  >
                    Save version
                  </button>
                </Wiggle>
              </div>
            </GlassCard>
          </div>
        </div>
      )}
    </motion.div>
  );
}

function StylesPage() {
  const [filter, setFilter] = useState('All styles');
  const [presetOpen, setPresetOpen] = useState(false);
  const [presetName, setPresetName] = useState('');
  const notify = useNotify();
  const filtered = useMemo(
    () => (filter === 'All styles' ? styles : styles.filter((style) => style.type.includes(filter))),
    [filter]
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="relative"
    >
      <Sticker emoji="🎨" className="-top-6 right-10" rotate={12} size="3.25rem" />
      <Starburst text="HOT" size="4rem" color="#FF307F" textColor="#F5F0E8" className="absolute top-10 right-40 hidden lg:flex" />

      <PageTitle
        eyebrow="Style Library"
        title={
          <>
            FIND THE FEELING
            <br />
            <span className="font-headline text-[clamp(2.5rem,6.5vw,5rem)] text-outline inline-block -rotate-1 my-1">
              EXPLOSIVE
            </span>
            <br />
            <span className="text-gradient-max font-display">BEFORE THE FIRST CUT.</span>
          </>
        }
        copy="A maximalist library of visual instincts, built by editors who refuse the boring and embrace the kinetic."
        action={
          <Wiggle>
            <button
              type="button"
              onClick={() => document.getElementById('style-grid')?.scrollIntoView({ behavior: 'smooth' })}
              data-testid="button-browse-styles"
              className="inline-flex items-center gap-2 border-4 border-[#2B59FF] bg-[#111111] px-5 py-3.5 font-display text-xs font-bold uppercase tracking-wider text-[#F5F0E8] shadow-[0_4px_0_#FFD400] hover:bg-[#2B59FF] hover:text-[#0A0A0A] transition-all"
            >
              Browse all <ArrowDownRight size={16} />
            </button>
          </Wiggle>
        }
      />

      <div className="mb-8 flex gap-3 overflow-x-auto pb-2 hide-scrollbar">
        {['All styles', 'Cinematic', 'Lifestyle', 'Fast / Raw', 'Editorial'].map((item) => (
          <Wiggle key={item}>
            <button
              type="button"
              onClick={() => setFilter(item)}
              data-testid={`button-filter-${item.toLowerCase().replaceAll(' ', '-')}`}
              className={`whitespace-nowrap border-3 px-5 py-2.5 font-display text-xs font-bold uppercase tracking-wider transition-all ${
                filter === item
                  ? 'border-[#FFD400] bg-[#FF307F] text-[#0A0A0A] shadow-[0_4px_0_#2B59FF]'
                  : 'border-white/20 bg-[#111111] text-[#F5F0E8]/70 hover:border-[#FFD400] hover:text-[#F5F0E8]'
              }`}
            >
              {item}
            </button>
          </Wiggle>
        ))}
      </div>

      <div id="style-grid" className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((style, index) => (
          <motion.div
            key={style.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            className="flex flex-col"
          >
            <StyleCard style={style} selected={false} onSelect={() => undefined} />
            <Wiggle className="w-full mt-3">
              <Link
                href="/create"
                data-testid={`link-use-style-${style.id}`}
                className="flex items-center justify-center gap-2 border-3 border-[#FFD400] bg-[#2B59FF] py-3 font-display text-xs font-bold uppercase tracking-wider text-[#F5F0E8] shadow-[0_4px_0_#FF307F] hover:bg-[#FFD400] hover:text-[#0A0A0A] transition-colors"
              >
                Use {style.name} <ArrowRight size={14} />
              </Link>
            </Wiggle>
          </motion.div>
        ))}
      </div>

      <GlassCard className="mt-12 flex flex-col gap-5 p-6 border-4 border-[#FF7A00] shadow-[0_8px_30px_rgba(255,122,0,0.25)] sm:flex-row sm:items-center sm:justify-between pattern-stripes">
        <div className="flex items-center gap-4">
          <div className="grid h-12 w-12 shrink-0 place-items-center border-3 border-[#0A0A0A] bg-[#FFD400] text-[#0A0A0A] shadow-[0_4px_0_#FF307F]">
            <Sparkles size={22} strokeWidth={2.5} />
          </div>
          <div>
            <div className="font-display text-lg font-bold uppercase text-[#F5F0E8]">
              HAVE A DISTINCT POINT OF VIEW?
            </div>
            <div className="mt-1 text-xs text-[#F5F0E8]/70">
              Mix two styles and mint a hyper-customized private preset for your channel.
            </div>
          </div>
        </div>
        <Wiggle>
          <button
            type="button"
            onClick={() => setPresetOpen(true)}
            data-testid="button-create-preset"
            className="whitespace-nowrap border-3 border-[#FFD400] bg-[#FF307F] px-5 py-3 font-display text-xs font-bold uppercase tracking-wider text-[#0A0A0A] shadow-[0_4px_0_#2B59FF] hover:bg-[#FFD400] transition-colors"
          >
            Create a preset <Plus size={14} className="ml-1 inline" />
          </button>
        </Wiggle>
      </GlassCard>

      <Modal open={presetOpen} title="NAME YOUR PRIVATE PRESET" onClose={() => setPresetOpen(false)}>
        <p className="mt-3 text-xs leading-relaxed text-[#F5F0E8]/70">
          Your preset will fuse the studio&apos;s active color rules with your raw sonic and cutting instinct.
        </p>
        <input
          autoFocus
          value={presetName}
          onChange={(e) => setPresetName(e.target.value)}
          placeholder="e.g. ULTRA GLITCH DISCO"
          data-testid="input-preset-name"
          className="mt-5 w-full border-3 border-[#FFD400] bg-[#0A0A0A] px-4 py-3.5 font-mono text-sm text-[#F5F0E8] outline-none placeholder:text-[#F5F0E8]/40 focus:border-[#FF307F]"
        />
        <div className="mt-6 flex justify-end gap-3">
          <Wiggle>
            <button
              type="button"
              onClick={() => setPresetOpen(false)}
              data-testid="button-cancel-preset"
              className="border-2 border-white/20 px-4 py-2.5 font-display text-xs font-bold uppercase tracking-wider text-[#F5F0E8] hover:bg-white/10"
            >
              Cancel
            </button>
          </Wiggle>
          <Wiggle>
            <button
              type="button"
              disabled={!presetName.trim()}
              onClick={() => {
                notify(`${presetName.trim()} saved to your private library.`, 'success');
                setPresetName('');
                setPresetOpen(false);
              }}
              data-testid="button-save-preset"
              className="border-3 border-[#FFD400] bg-[#00B37E] px-5 py-2.5 font-display text-xs font-bold uppercase tracking-wider text-[#0A0A0A] shadow-[0_4px_0_#FF307F] disabled:cursor-not-allowed disabled:opacity-40"
            >
              Save preset
            </button>
          </Wiggle>
        </div>
      </Modal>
    </motion.div>
  );
}

function ProjectsPage() {
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState('All projects');
  const visible = projects.filter(
    (project) =>
      project.title.toLowerCase().includes(query.toLowerCase()) &&
      (tab === 'All projects' || project.status === tab.slice(0, -1))
  );
  const notify = useNotify();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="relative"
    >
      <Sticker emoji="🎬" className="-top-6 right-16" rotate={-8} size="3.5rem" />
      <Starburst text="VAULT" size="4.25rem" color="#00B37E" textColor="#0A0A0A" className="absolute top-12 right-48 hidden lg:flex" />

      <PageTitle
        eyebrow="Your Archive"
        title={
          <>
            PROJECTS WITH
            <br />
            <span className="font-headline text-[clamp(2.5rem,6.5vw,5.5rem)] text-outline inline-block rotate-1 my-1">
              A PULSE
            </span>
            <br />
            <span className="text-gradient-max font-display">& RAW CHAOS.</span>
          </>
        }
        copy="Every cut pass, midnight experiment, and raw reel stored with uncompromised fidelity."
        action={
          <Wiggle>
            <Link
              href="/create"
              data-testid="link-projects-new-edit"
              className="inline-flex items-center gap-2 border-4 border-[#FFD400] bg-[#FF307F] px-6 py-4 font-display text-xs font-black uppercase tracking-wider text-[#0A0A0A] shadow-[0_6px_0_#2B59FF] hover:bg-[#FFD400] transition-colors cta-glow"
            >
              <Plus size={18} strokeWidth={3} /> NEW EDIT
            </Link>
          </Wiggle>
        }
      />

      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-2.5 overflow-x-auto pb-1 hide-scrollbar">
          {['All projects', 'Ready', 'Drafts'].map((item) => (
            <Wiggle key={item}>
              <button
                type="button"
                onClick={() => setTab(item)}
                data-testid={`button-project-tab-${item.toLowerCase().replace(' ', '-')}`}
                className={`border-3 px-5 py-2.5 font-display text-xs font-bold uppercase tracking-wider transition-all ${
                  tab === item
                    ? 'border-[#FFD400] bg-[#2B59FF] text-[#F5F0E8] shadow-[0_4px_0_#FF307F]'
                    : 'border-white/20 bg-[#111111] text-[#F5F0E8]/70 hover:border-white/40 hover:text-[#F5F0E8]'
                }`}
              >
                {item}
              </button>
            </Wiggle>
          ))}
        </div>
        <label className="flex items-center gap-2 border-3 border-[#2B59FF] bg-[#111111] px-3.5 py-1 text-[#F5F0E8]">
          <Search size={16} className="text-[#FFD400]" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search projects..."
            data-testid="input-project-search"
            className="w-full bg-transparent py-2 font-mono text-xs text-[#F5F0E8] outline-none placeholder:text-[#F5F0E8]/40"
          />
        </label>
      </div>

      {visible.length ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {visible.map((project, i) => (
            <motion.div
              key={project.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <ProjectCard project={project} />
            </motion.div>
          ))}
        </div>
      ) : (
        <GlassCard className="flex min-h-[300px] flex-col items-center justify-center p-8 text-center border-4 border-dashed border-[#FF307F]/40 pattern-checkerboard">
          <div className="grid h-16 w-16 place-items-center border-3 border-[#FFD400] bg-[#FF307F] text-[#0A0A0A] shadow-[0_4px_0_#2B59FF]">
            <FolderClock size={28} strokeWidth={2.5} />
          </div>
          <h2 className="mt-5 font-display text-xl font-bold uppercase text-[#F5F0E8]">
            NOTHING IN THIS FRAME
          </h2>
          <p className="mt-2 max-w-sm text-xs leading-relaxed text-[#F5F0E8]/70">
            No cuts match your query. Clear the search, or launch a bold new edit to feed the vault.
          </p>
          <Wiggle>
            <Link
              href="/create"
              data-testid="link-empty-new-project"
              className="mt-6 inline-flex border-3 border-[#FFD400] bg-[#00B37E] px-5 py-3 font-display text-xs font-bold uppercase tracking-wider text-[#0A0A0A] shadow-[0_4px_0_#FF307F]"
            >
              START AN EDIT
            </Link>
          </Wiggle>
        </GlassCard>
      )}

      <GlassCard className="mt-10 p-6 border-4 border-[#2B59FF] shadow-[0_8px_30px_rgba(43,89,255,0.2)]">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <div className="font-display text-sm font-bold uppercase tracking-wider text-[#F5F0E8]">
              LOCAL DEMO STORAGE
            </div>
            <div className="mt-1 font-mono text-xs text-[#FFD400]">
              6.8 GB used of 25 GB · 18.2 GB free
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="h-3 w-48 overflow-hidden border-2 border-white/20 bg-[#111111]">
              <div
                className="h-full w-[27%]"
                style={{ background: 'linear-gradient(90deg, #FF307F, #FFD400)' }}
              />
            </div>
            <Wiggle>
              <button
                type="button"
                onClick={() => notify('Storage details opened.', 'info')}
                data-testid="button-storage-details"
                className="font-display text-xs font-bold uppercase tracking-wider text-[#FFD400] hover:text-[#FF307F]"
              >
                Details <ArrowRight size={13} className="ml-1 inline" />
              </button>
            </Wiggle>
          </div>
        </div>
      </GlassCard>
    </motion.div>
  );
}

function PreferencesPage() {
  const notify = useNotify();
  const [autocap, setAutocap] = useState(true);
  const [smartCrop, setSmartCrop] = useState(true);
  const [music, setMusic] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="relative max-w-5xl"
    >
      <Sticker emoji="⚙️" className="-top-6 right-8" rotate={15} size="3rem" />

      <PageTitle
        eyebrow="Studio Preferences"
        title={
          <>
            DEFAULTS THAT
            <br />
            <span className="font-headline text-[clamp(2.5rem,6.5vw,5rem)] text-outline inline-block -rotate-1 my-1">
              ROAR
            </span>
            <br />
            <span className="text-gradient-max font-display">YOUR IDENTITY.</span>
          </>
        }
        copy="Fine-tune your editing instincts. These rules govern automated cuts, typography choices, and music beds."
      />

      <div className="grid gap-6 lg:grid-cols-[1.25fr_.75fr]">
        <GlassCard className="divide-y-3 divide-white/10 px-6 sm:px-8 border-4 border-[#FF307F] shadow-[0_8px_30px_rgba(255,48,127,0.25)]">
          <div className="py-6">
            <h2 className="font-display text-lg font-bold uppercase text-[#FFD400]">
              EDITORIAL INSTINCTS
            </h2>
            <p className="mt-1 text-xs text-[#F5F0E8]/70">
              Automated aesthetic choices StyleCut enforces during synthesis.
            </p>
          </div>

          <Toggle
            label="Auto-caption every edit"
            copy="Generate aggressive, high-contrast typography captions as part of the primary render."
            value={autocap}
            onChange={(v) => {
              setAutocap(v);
              notify(v ? 'Auto-captions enabled.' : 'Auto-captions paused.', 'success');
            }}
          />

          <Toggle
            label="Smart crop for 9:16"
            copy="Track focal points dynamically when re-framing widescreen footage for vertical dominance."
            value={smartCrop}
            onChange={(v) => {
              setSmartCrop(v);
              notify(v ? 'Smart crop enabled.' : 'Smart crop paused.', 'success');
            }}
          />

          <Toggle
            label="Suggest music beds"
            copy="Match high-energy sync beats to the rhythm and acceleration spikes in your clips."
            value={music}
            onChange={(v) => {
              setMusic(v);
              notify(v ? 'Music suggestions enabled.' : 'Music suggestions paused.', 'success');
            }}
          />

          <div className="py-6">
            <label className="font-display text-sm font-bold uppercase tracking-wider text-[#F5F0E8]">
              DEFAULT ASPECT RATIO
            </label>
            <div className="mt-4 grid grid-cols-3 gap-3">
              {['9:16', '1:1', '16:9'].map((item, i) => (
                <Wiggle key={item} className="w-full">
                  <button
                    type="button"
                    onClick={() => notify(`${item} is now your default output.`, 'success')}
                    data-testid={`button-output-${item.replace(':', '-')}`}
                    className={`w-full border-3 py-3 font-display text-xs font-bold uppercase tracking-wider transition-all ${
                      i === 0
                        ? 'border-[#FFD400] bg-[#FF307F] text-[#0A0A0A] shadow-[0_4px_0_#2B59FF]'
                        : 'border-white/20 bg-[#111111] text-[#F5F0E8]/70 hover:border-white/40 hover:text-[#F5F0E8]'
                    }`}
                  >
                    {item}
                    <span className="mt-1 block font-mono text-[10px] text-[#0A0A0A]/80">
                      {i === 0 ? 'Vertical' : i === 1 ? 'Square' : 'Landscape'}
                    </span>
                  </button>
                </Wiggle>
              ))}
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-6 sm:p-8 border-4 border-[#FFD400] shadow-[0_8px_30px_rgba(255,212,0,0.25)] flex flex-col justify-between pattern-polka">
          <div>
            <div className="flex items-center gap-2 font-display text-xs font-bold uppercase tracking-widest text-[#FF7A00]">
              <Mic2 size={16} /> CREATIVE SIGNAL
            </div>
            <div className="mt-6 font-display text-3xl font-black uppercase text-[#F5F0E8] leading-tight">
              RAW &amp; <br />
              <span className="text-gradient-max font-headline text-4xl">ELECTRIC.</span>
            </div>
            <p className="mt-4 text-xs leading-relaxed text-[#F5F0E8]/70">
              Your profile favors razor-sharp kinetic pacing, dynamic neon grading, and bass-heavy hit cuts that demand viewer engagement.
            </p>

            <div className="mt-8 space-y-3 font-mono text-xs">
              {[
                ['Pacing', 'Kinetic / Fast'],
                ['Color', 'Neon Ultra-Grade'],
                ['Text', 'Monoton / Bold'],
                ['Audio', 'Full Stems Sync'],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="flex items-center justify-between border-b border-white/10 pb-3"
                >
                  <span className="text-[#F5F0E8]/60">{label}</span>
                  <span className="font-bold text-[#FFD400]">{value}</span>
                </div>
              ))}
            </div>
          </div>

          <Wiggle className="w-full mt-8">
            <button
              type="button"
              onClick={() => notify('Your creative profile was recalibrated.', 'success')}
              data-testid="button-calibrate-signal"
              className="w-full border-3 border-[#0A0A0A] bg-[#FFD400] py-3.5 font-display text-xs font-black uppercase tracking-wider text-[#0A0A0A] shadow-[0_4px_0_#FF307F] hover:bg-[#FF307F] hover:text-[#0A0A0A] transition-colors"
            >
              RECALIBRATE SIGNAL
            </button>
          </Wiggle>
        </GlassCard>
      </div>
    </motion.div>
  );
}

function ProfilePage() {
  const notify = useNotify();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="relative max-w-6xl"
    >
      <Sticker emoji="⚡" className="-top-6 right-12" rotate={14} size="3.5rem" />
      <Starburst text="VIP" size="4.5rem" color="#FF307F" textColor="#0A0A0A" className="absolute top-8 right-40 hidden lg:flex" />

      <PageTitle
        eyebrow="Creator Profile"
        title={
          <>
            ARI RIVERA
            <br />
            <span className="font-headline text-[clamp(2.5rem,6.5vw,5.5rem)] text-outline inline-block -rotate-1 my-1">
              COMMANDS
            </span>
            <br />
            <span className="text-gradient-max font-display">THE TIMELINE.</span>
          </>
        }
        copy="Your digital signature and creative imprint across short-form storytelling."
        action={
          <Wiggle>
            <button
              type="button"
              onClick={() => notify('Profile changes are ready to edit.', 'info')}
              data-testid="button-edit-profile"
              className="border-4 border-[#2B59FF] bg-[#111111] px-6 py-3.5 font-display text-xs font-bold uppercase tracking-wider text-[#F5F0E8] shadow-[0_4px_0_#FFD400] hover:bg-[#2B59FF] hover:text-[#0A0A0A] transition-colors"
            >
              EDIT PROFILE
            </button>
          </Wiggle>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[.85fr_1.15fr]">
        <GlassCard className="relative p-6 sm:p-8 border-4 border-[#FF307F] shadow-[0_8px_30px_rgba(255,48,127,0.25)] pattern-stripes">
          <div className="flex items-center gap-5">
            <div className="grid h-20 w-20 place-items-center border-4 border-[#0A0A0A] bg-[#FF307F] font-display text-2xl font-black text-[#0A0A0A] shadow-[0_4px_0_#FFD400]">
              AR
            </div>
            <div>
              <div className="font-display text-2xl font-black uppercase text-[#F5F0E8]">
                Ari Rivera
              </div>
              <div className="mt-1 font-mono text-xs font-bold text-[#FFD400]">
                @aririvera · New York City
              </div>
            </div>
          </div>
          <p className="mt-6 text-xs leading-relaxed text-[#F5F0E8]/80">
            Director, motion editor, and maximalist visual archivist. Sculpting high-voltage short reels for hyper-stimulated audiences.
          </p>
          <div className="mt-8 flex gap-3">
            <span className="border-2 border-[#FFD400] bg-[#FF307F]/20 px-3.5 py-1.5 font-display text-[10px] font-bold uppercase tracking-wider text-[#FFD400]">
              Director
            </span>
            <span className="border-2 border-[#00B37E] bg-[#00B37E]/20 px-3.5 py-1.5 font-display text-[10px] font-bold uppercase tracking-wider text-[#00B37E]">
              Kinetic-First
            </span>
          </div>
        </GlassCard>

        <GlassCard className="p-6 sm:p-8 border-4 border-[#2B59FF] shadow-[0_8px_30px_rgba(43,89,255,0.25)]">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-bold uppercase text-[#FFD400]">
              STUDIO SIGNATURE
            </h2>
            <Sparkles size={18} className="text-[#FF307F]" />
          </div>

          <div className="mt-8 grid gap-6 sm:grid-cols-2">
            <div>
              <div className="mb-2 flex justify-between font-mono text-xs">
                <span className="text-[#F5F0E8]/70">Visual Tension</span>
                <span className="font-black text-[#FF307F]">84%</span>
              </div>
              <div className="h-2.5 overflow-hidden border border-white/20 bg-[#111111]">
                <div className="h-full w-[84%] bg-[#FF307F]" />
              </div>
            </div>

            <div>
              <div className="mb-2 flex justify-between font-mono text-xs">
                <span className="text-[#F5F0E8]/70">Emotional Pace</span>
                <span className="font-black text-[#FFD400]">71%</span>
              </div>
              <div className="h-2.5 overflow-hidden border border-white/20 bg-[#111111]">
                <div className="h-full w-[71%] bg-[#FFD400]" />
              </div>
            </div>

            <div>
              <div className="mb-2 flex justify-between font-mono text-xs">
                <span className="text-[#F5F0E8]/70">Sound Instinct</span>
                <span className="font-black text-[#00B37E]">63%</span>
              </div>
              <div className="h-2.5 overflow-hidden border border-white/20 bg-[#111111]">
                <div className="h-full w-[63%] bg-[#00B37E]" />
              </div>
            </div>

            <div>
              <div className="mb-2 flex justify-between font-mono text-xs">
                <span className="text-[#F5F0E8]/70">Hook Acceleration</span>
                <span className="font-black text-[#2B59FF]">78%</span>
              </div>
              <div className="h-2.5 overflow-hidden border border-white/20 bg-[#111111]">
                <div className="h-full w-[78%] bg-[#2B59FF]" />
              </div>
            </div>
          </div>

          <div className="mt-8 border-t-3 border-white/10 pt-5 font-mono text-xs text-[#F5F0E8]/70">
            Signature Style:{' '}
            <span className="font-display font-bold uppercase text-[#FFD400]">Neon Noir</span>
            <span className="mx-2 text-[#FF307F]">★</span> 12 edits this month
          </div>
        </GlassCard>
      </div>

      <div className="mt-8 grid gap-6 sm:grid-cols-3">
        <StatTile label="Total edits" value="142" change="+12.5%" color="#FF307F" />
        <StatTile label="Minutes shaped" value="38h 12m" change="+19.1%" color="#FFD400" />
        <StatTile label="Followers reached" value="284k" change="+31.6%" color="#2B59FF" />
      </div>
    </motion.div>
  );
}

function SettingsPage() {
  const notify = useNotify();
  const [motionActive, setMotionActive] = useState(true);
  const [sounds, setSounds] = useState(true);
  const [quality, setQuality] = useState('Balanced');

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="relative max-w-5xl"
    >
      <Sticker emoji="🛠️" className="-top-6 right-8" rotate={-10} size="3.25rem" />

      <PageTitle
        eyebrow="Settings"
        title={
          <>
            THE ENGINE ROOM
            <br />
            <span className="font-headline text-[clamp(2.5rem,6.5vw,5rem)] text-outline inline-block rotate-1 my-1">
              BEHIND
            </span>
            <br />
            <span className="text-gradient-max font-display">THE CUT.</span>
          </>
        }
        copy="Configure performance thresholds, storage behavior, and visual acceleration parameters."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <GlassCard className="divide-y-3 divide-white/10 px-6 sm:px-8 border-4 border-[#2B59FF] shadow-[0_8px_30px_rgba(43,89,255,0.25)]">
          <div className="py-6">
            <h2 className="font-display text-lg font-bold uppercase text-[#FFD400]">
              WORKSPACE FEEL
            </h2>
            <p className="mt-1 text-xs text-[#F5F0E8]/70">
              Control animations, audio cues, and renderer fidelity.
            </p>
          </div>

          <Toggle
            label="Motion and transitions"
            copy="Keep hyperactive layout transitions and kinetic rendering moments."
            value={motionActive}
            onChange={(v) => {
              setMotionActive(v);
              notify(v ? 'Motion restored.' : 'Motion reduced.', 'success');
            }}
          />

          <Toggle
            label="Interface sounds"
            copy="Play punchy audio feedback when renders finish or milestones complete."
            value={sounds}
            onChange={(v) => {
              setSounds(v);
              notify(v ? 'Interface sounds enabled.' : 'Interface sounds muted.', 'success');
            }}
          />

          <div className="py-6">
            <label className="font-display text-sm font-bold uppercase tracking-wider text-[#F5F0E8]">
              RENDER QUALITY
            </label>
            <div className="mt-4 flex gap-3">
              {['Fast', 'Balanced', 'Max'].map((item) => (
                <Wiggle key={item} className="flex-1">
                  <button
                    type="button"
                    onClick={() => {
                      setQuality(item);
                      notify(`${item} render quality selected.`, 'success');
                    }}
                    data-testid={`button-quality-${item.toLowerCase()}`}
                    className={`w-full border-3 py-3 font-display text-xs font-bold uppercase tracking-wider transition-all ${
                      quality === item
                        ? 'border-[#FFD400] bg-[#FF307F] text-[#0A0A0A] shadow-[0_4px_0_#2B59FF]'
                        : 'border-white/20 bg-[#111111] text-[#F5F0E8]/70 hover:border-white/40 hover:text-[#F5F0E8]'
                    }`}
                  >
                    {item}
                  </button>
                </Wiggle>
              ))}
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-6 sm:p-8 border-4 border-[#FFD400] shadow-[0_8px_30px_rgba(255,212,0,0.25)]">
          <h2 className="font-display text-lg font-bold uppercase text-[#FF307F]">
            ACCOUNT &amp; PRIVACY
          </h2>
          <div className="mt-6 space-y-3">
            {[
              {
                id: 'email',
                title: 'Email preferences',
                copy: 'Weekly studio drops and release dispatches',
                icon: ArrowRight,
                action: () => notify('Email preferences opened.', 'info'),
              },
              {
                id: 'privacy',
                title: 'Privacy & data',
                copy: 'Local sandbox mode · zero telemetry leaks',
                icon: LockKeyhole,
                action: () => notify('Your local project archive is private by default.', 'success'),
              },
              {
                id: 'shortcuts',
                title: 'Keyboard shortcuts',
                copy: '⌘N new edit · ⌘K search · Space preview',
                icon: HelpCircle,
                action: () => notify('Keyboard shortcuts: ⌘N new edit · ⌘K search · Space preview.', 'info'),
              },
            ].map((item) => (
              <Wiggle key={item.id} className="w-full">
                <button
                  type="button"
                  onClick={item.action}
                  data-testid={`button-${item.id === 'shortcuts' ? 'keyboard-shortcuts' : item.id === 'privacy' ? 'privacy-details' : 'email-preferences'}`}
                  className="flex w-full items-center justify-between border-3 border-white/20 bg-[#111111] p-4 text-left hover:border-[#FFD400] hover:bg-[#2B59FF]/10 transition-colors"
                >
                  <div>
                    <span className="block font-display text-sm font-bold uppercase text-[#F5F0E8]">
                      {item.title}
                    </span>
                    <span className="mt-1 block font-mono text-[10px] text-[#F5F0E8]/60">
                      {item.copy}
                    </span>
                  </div>
                  <item.icon size={16} className="text-[#FFD400]" />
                </button>
              </Wiggle>
            ))}
          </div>

          <div className="mt-8 border-t-3 border-white/10 pt-6">
            <Wiggle>
              <button
                type="button"
                onClick={() => notify('You are on the latest maximalist version of StyleCut.', 'success')}
                data-testid="button-check-updates"
                className="font-display text-xs font-bold uppercase tracking-wider text-[#FFD400] hover:text-[#FF307F]"
              >
                Check for updates <ArrowRight size={13} className="ml-1 inline" />
              </button>
            </Wiggle>
          </div>
        </GlassCard>
      </div>
    </motion.div>
  );
}

function NotFoundPage() {
  return (
    <div className="relative grid min-h-[70vh] place-items-center text-center">
      <Sticker emoji="⚠️" className="top-12 left-1/4" rotate={-15} size="4rem" />
      <Sticker emoji="💥" className="bottom-16 right-1/4" rotate={20} size="3.5rem" />

      <div>
        <div className="font-mono text-xs font-black uppercase tracking-[.3em] text-[#FF7A00]">
          ERROR / FRAME NOT FOUND
        </div>
        <h1 className="mt-4 font-headline text-[clamp(4rem,10vw,8rem)] text-outline-blue">
          404
        </h1>
        <div className="font-display text-2xl font-black uppercase text-[#F5F0E8]">
          THIS CUT GOT LOST IN THE VAULT.
        </div>
        <p className="mt-3 text-xs text-[#F5F0E8]/70">
          The requested coordinate has no rendered footage. Return to the command center.
        </p>
        <Wiggle className="mt-8">
          <Link
            href="/"
            data-testid="link-not-found-home"
            className="inline-flex border-4 border-[#FFD400] bg-[#FF307F] px-6 py-4 font-display text-xs font-black uppercase tracking-wider text-[#0A0A0A] shadow-[0_6px_0_#2B59FF] hover:bg-[#FFD400] transition-colors"
          >
            BACK TO OVERVIEW
          </Link>
        </Wiggle>
      </div>
    </div>
  );
}

function CreateStudioPage() {
  const notify = useNotify();
  const [stage, setStage] = useState(1);
  const [fileName, setFileName] = useState('');
  const [progress, setProgress] = useState(0);
  const [selectedStyle, setSelectedStyle] = useState(styles[0]);
  const [generating, setGenerating] = useState(false);

  const goToTrends = () => {
    if (!fileName || progress < 100) {
      notify('Add a complete upload before choosing a trend.', 'info');
      return;
    }
    setStage(2);
  };

  const generate = () => {
    setGenerating(true);
    setStage(3);
    notify('StyleCut is finding the rhythm in your footage.', 'info');
    window.setTimeout(() => {
      setGenerating(false);
      setStage(4);
      notify('Your first cut is ready to preview.', 'success');
    }, 2800);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="relative"
    >
      <Sticker emoji="⚡" className="-top-6 right-16" rotate={12} size="3.25rem" />

      <PageTitle
        eyebrow="Create Studio"
        title={
          <>
            RAW FOOTAGE TO
            <br />
            <span className="font-headline text-[clamp(2.5rem,6.5vw,5.5rem)] text-outline inline-block -rotate-1 my-1">
              HIGH VOLTAGE
            </span>
            <br />
            <span className="text-gradient-max font-display">CINEMA.</span>
          </>
        }
        copy="Four deliberate stages. Your footage, high-energy trend matching, instant timeline synthesis."
        action={
          <div className="flex items-center gap-2 border-2 border-[#00B37E] bg-[#00B37E]/10 px-3.5 py-2 font-mono text-xs font-bold text-[#00B37E]">
            <LockKeyhole size={14} /> LOCAL WORKSPACE
          </div>
        }
      />

      <StepRail current={stage} setCurrent={setStage} />

      {stage === 1 && (
        <div className="grid gap-6 xl:grid-cols-[1.4fr_.6fr]">
          <GlassCard className="p-6 sm:p-8 border-4 border-[#FF307F] shadow-[0_8px_30px_rgba(255,48,127,0.25)]">
            <div className="mb-6 flex items-start justify-between">
              <div>
                <h2 className="font-display text-xl font-bold uppercase text-[#F5F0E8]">
                  UPLOAD RAW FOOTAGE
                </h2>
                <p className="mt-1 text-xs text-[#F5F0E8]/70">
                  Drop your uncut files. Our engine scans every transient and focal motion.
                </p>
              </div>
              <span className="border-2 border-[#FFD400] bg-[#FFD400] px-3 py-1 font-mono text-xs font-black text-[#0A0A0A]">
                01 / 04
              </span>
            </div>
            <UploadDropzone
              fileName={fileName}
              setFileName={setFileName}
              progress={progress}
              setProgress={setProgress}
            />
            <div className="mt-6 flex justify-end">
              <Wiggle>
                <button
                  type="button"
                  onClick={goToTrends}
                  data-testid="button-next-trends"
                  className="inline-flex items-center gap-2 border-4 border-[#FFD400] bg-[#FF307F] px-6 py-4 font-display text-xs font-black uppercase tracking-wider text-[#0A0A0A] shadow-[0_6px_0_#2B59FF] hover:bg-[#FFD400] transition-colors cta-glow"
                >
                  CHOOSE A TREND <ArrowRight size={16} strokeWidth={3} />
                </button>
              </Wiggle>
            </div>
          </GlassCard>

          <GlassCard className="p-6 sm:p-8 border-4 border-[#2B59FF] shadow-[0_8px_30px_rgba(43,89,255,0.25)] pattern-polka">
            <div className="flex items-center gap-2 font-display text-xs font-bold uppercase tracking-widest text-[#FF7A00]">
              <Gauge size={16} /> STUDIO TIPS
            </div>
            <div className="mt-8 space-y-6">
              {[
                ['01', 'Long takes excel', 'Unbroken video gives the AI rhythm detectors more raw surface area.'],
                ['02', 'Crisp transients', 'Punchy audio spikes trigger surgical visual drop cuts automatically.'],
                ['03', '9:16 dominance', 'Optimized for high-impact vertical feeds out of the gate.'],
              ].map(([num, title, copy]) => (
                <div key={num} className="flex gap-4">
                  <span className="font-mono text-xs font-black text-[#FF307F]">{num}</span>
                  <div>
                    <div className="font-display text-sm font-bold uppercase text-[#FFD400]">{title}</div>
                    <p className="mt-1 text-xs leading-relaxed text-[#F5F0E8]/70">{copy}</p>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      )}

      {stage === 2 && (
        <div className="grid gap-6 xl:grid-cols-[1fr_390px]">
          <GlassCard className="p-6 sm:p-8 border-4 border-[#FFD400] shadow-[0_8px_30px_rgba(255,212,0,0.25)]">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="font-display text-xl font-bold uppercase text-[#F5F0E8]">
                  SELECT YOUR TREND
                </h2>
                <p className="mt-1 font-mono text-xs text-[#FFD400]">
                  {fileName || 'Your footage'} · 04:18 · 42 MB
                </p>
              </div>
              <Wiggle>
                <button
                  type="button"
                  onClick={() => setStage(1)}
                  data-testid="button-back-upload"
                  className="border-2 border-white/20 px-3.5 py-1.5 font-display text-xs font-bold uppercase tracking-wider text-[#F5F0E8] hover:bg-white/10"
                >
                  Back to upload
                </button>
              </Wiggle>
            </div>

            <div className="grid gap-6 sm:grid-cols-2">
              {styles.map((style) => (
                <ReferenceStyleCard
                  key={style.id}
                  style={style}
                  selected={selectedStyle.id === style.id}
                  onSelect={() => setSelectedStyle(style)}
                />
              ))}
            </div>

            <div className="mt-8 flex justify-end">
              <Wiggle>
                <button
                  type="button"
                  onClick={generate}
                  data-testid="button-generate-edit"
                  className="group inline-flex items-center gap-2 border-4 border-[#FFD400] bg-[#FF307F] px-8 py-4 font-display text-sm font-black uppercase tracking-wider text-[#0A0A0A] shadow-[0_6px_0_#2B59FF] hover:bg-[#FFD400] transition-colors cta-glow"
                >
                  SYNTHESIZE EDIT <Sparkles size={18} strokeWidth={3} className="transition group-hover:rotate-12" />
                </button>
              </Wiggle>
            </div>
          </GlassCard>

          <ChatAssistant />
        </div>
      )}

      {stage === 3 && (
        <GlassCard className="relative min-h-[540px] overflow-hidden p-8 sm:p-14 border-4 border-[#FF307F] shadow-[0_8px_40px_rgba(255,48,127,0.35)] pattern-checkerboard">
          <div className="relative z-10 mx-auto flex max-w-lg flex-col items-center text-center">
            <div className="relative grid h-28 w-28 place-items-center border-4 border-[#FFD400] bg-[#FF307F] text-[#0A0A0A] shadow-[0_8px_0_#2B59FF]">
              <WandSparkles size={40} strokeWidth={2.5} />
            </div>
            <div className="mt-8 font-mono text-xs font-black uppercase tracking-[.3em] text-[#FF7A00]">
              {generating ? 'SYNTHESIZING FIRST PASS' : 'SYNTHESIS COMPLETE'}
            </div>
            <h2 className="mt-3 font-headline text-[clamp(2.5rem,6vw,4.5rem)] text-[#F5F0E8] leading-tight">
              {generating ? 'SCULPTING...' : 'CUT READY!'}
            </h2>
            <p className="mt-3 text-xs leading-relaxed text-[#F5F0E8]/70">
              {generating
                ? 'Extracting high-velocity motion vectors, framing faces, and aligning audio beatdrops.'
                : 'Your kinetic first pass is ready. Inspect every frame and export.'}
            </p>

            {generating && (
              <div className="mt-10 w-full">
                <div className="mb-2 flex justify-between font-mono text-xs">
                  <span className="text-[#F5F0E8]/70 uppercase">ASSEMBLING MOMENTS</span>
                  <span className="font-black text-[#FFD400]">LIVE</span>
                </div>
                <div className="h-3 overflow-hidden border-2 border-white/20 bg-[#111111]">
                  <div
                    className="h-full w-full sweep"
                    style={{ background: 'linear-gradient(90deg, #FF307F, #FFD400, #2B59FF)' }}
                  />
                </div>
                <div className="mt-8 grid grid-cols-3 gap-3">
                  {['Reading clips', 'Mapping the beat', 'Balancing color'].map((item, i) => (
                    <div
                      key={item}
                      className="border-2 border-white/20 bg-[#111111] p-3 text-center"
                    >
                      <span className="mb-1 block font-mono text-xs font-black text-[#FFD400]">
                        0{i + 1}
                      </span>
                      <span className="font-display text-[11px] font-bold uppercase text-[#F5F0E8]">
                        {item}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </GlassCard>
      )}

      {stage === 4 && (
        <div className="grid gap-6 xl:grid-cols-[1.2fr_.8fr]">
          <GlassCard className="p-4 sm:p-6 border-4 border-[#FFD400] shadow-[0_8px_30px_rgba(255,212,0,0.25)]">
            <div className="relative aspect-[9/12] max-h-[620px] overflow-hidden border-4 border-[#0A0A0A] bg-[linear-gradient(140deg,#0A0A0A,#FF307F_45%,#2B59FF)] shadow-[0_8px_0_#FFD400]">
              <div className="absolute left-4 top-4 border-2 border-[#0A0A0A] bg-[#FFD400] px-3 py-1 font-mono text-xs font-black text-[#0A0A0A]">
                STYLECUT / 01
              </div>

              <Wiggle className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
                <button
                  type="button"
                  onClick={() => notify('Cinema mode opened.', 'success')}
                  data-testid="button-play-result"
                  className="grid h-20 w-20 place-items-center border-4 border-[#0A0A0A] bg-[#FFD400] text-[#0A0A0A] shadow-[0_6px_0_#FF307F] hover:bg-[#FF307F] transition-colors"
                >
                  <Play size={28} fill="currentColor" />
                </button>
              </Wiggle>

              <div className="absolute inset-x-5 bottom-5">
                <div className="mb-2 text-right font-mono text-xs font-bold text-[#F5F0E8]">
                  00:42 / 00:42
                </div>
                <div className="h-2 overflow-hidden border border-white/40 bg-black/40">
                  <div className="h-full w-full bg-[#FFD400]" />
                </div>
                <div className="mt-3 flex items-center justify-between font-mono text-xs text-[#F5F0E8]">
                  <span className="font-bold text-[#FFD400]">{selectedStyle.name} / FIRST PASS</span>
                  <span className="flex items-center gap-1">
                    <Volume2 size={14} /> 84%
                  </span>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 pt-5">
              <div>
                <div className="font-display text-base font-bold uppercase text-[#F5F0E8]">
                  The city is still awake
                </div>
                <div className="mt-1 font-mono text-xs text-[#FFD400]">
                  First pass · 9:16 · 1080 × 1920
                </div>
              </div>
              <div className="flex gap-3">
                <Wiggle>
                  <button
                    type="button"
                    onClick={() => notify('Download queued for your local demo.', 'success')}
                    data-testid="button-download-result"
                    className="grid h-10 w-10 place-items-center border-3 border-[#FFD400] bg-[#111111] text-[#F5F0E8] hover:bg-[#FFD400] hover:text-[#0A0A0A] transition-colors"
                  >
                    <Download size={18} />
                  </button>
                </Wiggle>
                <Wiggle>
                  <button
                    type="button"
                    onClick={() => notify('Share link copied to clipboard.', 'success')}
                    data-testid="button-share-result"
                    className="grid h-10 w-10 place-items-center border-3 border-[#2B59FF] bg-[#111111] text-[#F5F0E8] hover:bg-[#2B59FF] hover:text-[#0A0A0A] transition-colors"
                  >
                    <Share2 size={18} />
                  </button>
                </Wiggle>
              </div>
            </div>
          </GlassCard>

          <div className="space-y-6">
            <GlassCard className="p-6 border-4 border-[#2B59FF] shadow-[0_8px_30px_rgba(43,89,255,0.25)]">
              <div className="flex items-center justify-between font-display text-sm font-bold uppercase text-[#FFD400]">
                <span>Before / After</span>
                <Eye size={18} className="text-[#FF307F]" />
              </div>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <div>
                  <div className="aspect-[9/12] border-2 border-white/20 bg-[linear-gradient(145deg,#222,#444)]" />
                  <div className="mt-2 font-mono text-[10px] font-black uppercase text-[#F5F0E8]/50">
                    Raw
                  </div>
                </div>
                <div>
                  <div className="aspect-[9/12] border-2 border-[#FFD400] bg-[linear-gradient(145deg,#0A0A0A,#FF307F_50%,#2B59FF)] shadow-[0_4px_16px_rgba(255,48,127,0.3)]" />
                  <div className="mt-2 font-mono text-[10px] font-black uppercase text-[#FFD400]">
                    Edited
                  </div>
                </div>
              </div>
              <div className="mt-6 space-y-3 font-mono text-xs">
                {[
                  ['Scored moments', '14 / 84 clips'],
                  ['Captions', 'Ready'],
                  ['Trend', selectedStyle.name],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    className="flex items-center justify-between border-t border-white/10 pt-3"
                  >
                    <span className="text-[#F5F0E8]/60">{label}</span>
                    <span className="font-bold text-[#FFD400]">{value}</span>
                  </div>
                ))}
              </div>
            </GlassCard>

            <GlassCard className="p-6 border-4 border-[#00B37E] shadow-[0_8px_30px_rgba(0,179,126,0.25)]">
              <div className="flex items-center gap-2 font-display text-sm font-bold uppercase text-[#F5F0E8]">
                <Sparkles size={16} className="text-[#FFD400]" /> MAKE IT YOURS
              </div>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <Wiggle className="w-full">
                  <button
                    type="button"
                    onClick={() => setStage(2)}
                    data-testid="button-adjust-result"
                    className="w-full border-3 border-white/20 px-3 py-3 font-display text-xs font-bold uppercase tracking-wider text-[#F5F0E8] hover:bg-[#FF307F] hover:text-[#0A0A0A] transition-colors"
                  >
                    Choose another trend
                  </button>
                </Wiggle>
                <Wiggle className="w-full">
                  <button
                    type="button"
                    onClick={() => notify('Version 01 saved to Projects.', 'success')}
                    data-testid="button-save-result"
                    className="w-full border-3 border-[#FFD400] bg-[#FF307F] px-3 py-3 font-display text-xs font-bold uppercase tracking-wider text-[#0A0A0A] shadow-[0_4px_0_#2B59FF] hover:bg-[#FFD400] transition-colors"
                  >
                    Save version
                  </button>
                </Wiggle>
              </div>
            </GlassCard>
          </div>
        </div>
      )}
    </motion.div>
  );
}

function TrendsPage() {
  const [filter, setFilter] = useState('All trends');
  const filtered = useMemo(
    () => (filter === 'All trends' ? styles : styles.filter((style) => style.type.includes(filter))),
    [filter]
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="relative"
    >
      <Sticker emoji="🔥" className="-top-6 right-10" rotate={-12} size="3.25rem" />
      <Starburst text="TOP" size="4rem" color="#FFD400" textColor="#0A0A0A" className="absolute top-10 right-44 hidden lg:flex" />

      <PageTitle
        eyebrow="Trends"
        title={
          <>
            RADICAL
            <br />
            <span className="font-headline text-[clamp(2.5rem,6.5vw,5.5rem)] text-outline inline-block rotate-1 my-1">
              TRENDS
            </span>
            <br />
            <span className="text-gradient-max font-display">BEFORE THE CUT.</span>
          </>
        }
        copy="Browse hyper-viral editing aesthetics, then upload reference footage to command StyleCut."
        action={
          <Wiggle>
            <Link
              href="/create"
              data-testid="link-trends-create"
              className="inline-flex items-center gap-2 border-4 border-[#FFD400] bg-[#FF307F] px-6 py-4 font-display text-xs font-black uppercase tracking-wider text-[#0A0A0A] shadow-[0_6px_0_#2B59FF] hover:bg-[#FFD400] transition-colors cta-glow"
            >
              <Plus size={18} strokeWidth={3} /> CREATE WITH A TREND
            </Link>
          </Wiggle>
        }
      />

      <div className="mb-8 flex gap-3 overflow-x-auto pb-2 hide-scrollbar">
        {['All trends', 'Cinematic', 'Lifestyle', 'Fast / Raw', 'Editorial'].map((item) => (
          <Wiggle key={item}>
            <button
              type="button"
              key={item}
              onClick={() => setFilter(item)}
              data-testid={`button-filter-${item.toLowerCase().replaceAll(' ', '-')}`}
              className={`whitespace-nowrap border-3 px-5 py-2.5 font-display text-xs font-bold uppercase tracking-wider transition-all ${
                filter === item
                  ? 'border-[#FFD400] bg-[#FF307F] text-[#0A0A0A] shadow-[0_4px_0_#2B59FF]'
                  : 'border-white/20 bg-[#111111] text-[#F5F0E8]/70 hover:border-[#FFD400] hover:text-[#F5F0E8]'
              }`}
            >
              {item}
            </button>
          </Wiggle>
        ))}
      </div>

      <GlassCard className="mb-8 flex items-center gap-5 p-5 sm:p-6 border-4 border-[#00B37E] shadow-[0_8px_30px_rgba(0,179,126,0.25)] pattern-stripes">
        <div className="grid h-12 w-12 shrink-0 place-items-center border-3 border-[#0A0A0A] bg-[#FFD400] text-[#0A0A0A] shadow-[0_4px_0_#FF307F]">
          <UploadCloud size={24} strokeWidth={2.5} />
        </div>
        <div>
          <div className="font-display text-base font-bold uppercase text-[#F5F0E8]">
            MAKE IT YOURS WITH REFERENCE VIDEO
          </div>
          <div className="mt-1 text-xs text-[#F5F0E8]/70">
            Each trend features a direct reference upload slot. Your creative seeds remain confidential in this workspace.
          </div>
        </div>
      </GlassCard>

      <div id="trend-grid" className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((style, index) => (
          <motion.div
            key={style.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
          >
            <ReferenceStyleCard style={style} selected={false} onSelect={() => undefined} />
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

function Router() {
  return (
    <Shell>
      <ErrorBoundary resetKey={window.location.pathname}>
        <Switch>
          <Route path="/" component={Dashboard} />
          <Route path="/create" component={CreateStudioPage} />
          <Route path="/styles" component={TrendsPage} />
          <Route path="/projects" component={ProjectsPage} />
          <Route path="/preferences" component={PreferencesPage} />
          <Route path="/profile" component={ProfilePage} />
          <Route path="/settings" component={SettingsPage} />
          <Route component={NotFoundPage} />
        </Switch>
      </ErrorBoundary>
    </Shell>
  );
}

function App() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const notify = (message: string, tone: Toast['tone'] = 'info') => {
    const id = Date.now();
    setToasts((current) => [...current.slice(-2), { id, message, tone }]);
    window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 3600);
  };

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <ToastContext.Provider value={notify}>
          <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
            <Router />
          </WouterRouter>
          <Toaster />
          <ToastStack toasts={toasts} dismiss={(id) => setToasts((current) => current.filter((toast) => toast.id !== id))} />
        </ToastContext.Provider>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;

