import React, { useState } from 'react';
import { format } from 'date-fns';
import { CalendarIcon, Clock3, Globe } from 'lucide-react';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';

const SCHEDULE_PRESETS = [
  { value: 'every_minute', label: 'Every Minute', cron: '* * * * *' },
  { value: 'every_5_min', label: 'Every 5 Minutes', cron: '*/5 * * * *' },
  { value: 'every_15_min', label: 'Every 15 Minutes', cron: '*/15 * * * *' },
  { value: 'every_30_min', label: 'Every 30 Minutes', cron: '*/30 * * * *' },
  { value: 'hourly', label: 'Hourly', cron: '0 * * * *' },
  { value: 'daily', label: 'Daily', cron: '0 0 * * *' },
  { value: 'weekly', label: 'Weekly', cron: '0 0 * * 1' },
  { value: 'monthly', label: 'Monthly', cron: '0 0 1 * *' },
  { value: 'custom', label: 'Custom Date & Time', cron: '' },
] as const;

const TIMEZONES = [
  { value: 'America/New_York', label: 'EST (New York)' },
  { value: 'America/Chicago', label: 'CST (Chicago)' },
  { value: 'America/Denver', label: 'MST (Denver)' },
  { value: 'America/Los_Angeles', label: 'PST (Los Angeles)' },
  { value: 'UTC', label: 'UTC' },
  { value: 'Europe/London', label: 'GMT (London)' },
  { value: 'Europe/Paris', label: 'CET (Paris)' },
  { value: 'Asia/Tokyo', label: 'JST (Tokyo)' },
  { value: 'Asia/Shanghai', label: 'CST (Shanghai)' },
  { value: 'Asia/Kolkata', label: 'IST (Kolkata)' },
  { value: 'Australia/Sydney', label: 'AEST (Sydney)' },
];

interface ScheduleEditorProps {
  schedule: string;
  timezone?: string;
  nextRunAt?: string | null;
  onChange: (schedule: string, timezone: string) => void;
}

function detectPresetFromCron(cron: string): string {
  const preset = SCHEDULE_PRESETS.find((p) => p.cron === cron);
  return preset ? preset.value : 'custom';
}

function detectLocalTimezone(): string {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const match = TIMEZONES.find((t) => t.value === tz);
  return match ? match.value : 'UTC';
}

export function ScheduleEditor({ schedule, timezone, nextRunAt, onChange }: ScheduleEditorProps) {
  const [preset, setPreset] = useState(() => detectPresetFromCron(schedule));
  const [customCron, setCustomCron] = useState(schedule);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(
    nextRunAt ? new Date(nextRunAt) : undefined
  );
  const [timeValue, setTimeValue] = useState(() => {
    if (nextRunAt) {
      const d = new Date(nextRunAt);
      return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    }
    return '09:00';
  });
  const [tz, setTz] = useState(timezone || detectLocalTimezone());
  const [calendarOpen, setCalendarOpen] = useState(false);

  const handlePresetChange = (newPreset: string) => {
    setPreset(newPreset);
    const match = SCHEDULE_PRESETS.find((p) => p.value === newPreset);
    if (match && match.value !== 'custom') {
      setCustomCron(match.cron);
      onChange(match.cron, tz);
    }
  };

  const handleTimezoneChange = (newTz: string) => {
    setTz(newTz);
    const currentCron = preset === 'custom' ? customCron : SCHEDULE_PRESETS.find(p => p.value === preset)?.cron || customCron;
    onChange(currentCron, newTz);
  };

  const buildCronFromDateTime = (date: Date | undefined, time: string): string => {
    const [hours, minutes] = time.split(':').map(Number);
    if (date) {
      return `${minutes} ${hours} ${date.getDate()} ${date.getMonth() + 1} *`;
    }
    // Time-only: run daily at this time
    return `${minutes} ${hours} * * *`;
  };

  const handleDateSelect = (date: Date | undefined) => {
    setSelectedDate(date);
    setCalendarOpen(false);
    if (preset === 'custom') {
      const cron = buildCronFromDateTime(date, timeValue);
      setCustomCron(cron);
      onChange(cron, tz);
    }
  };

  const handleTimeChange = (newTime: string) => {
    setTimeValue(newTime);
    if (preset === 'custom') {
      const cron = buildCronFromDateTime(selectedDate, newTime);
      setCustomCron(cron);
      onChange(cron, tz);
    }
  };

  return (
    <div className="space-y-3">
      {/* Preset Selector */}
      <div>
        <label className="text-[11px] font-medium text-muted-foreground block mb-1.5">Frequency</label>
        <select
          value={preset}
          onChange={(e) => handlePresetChange(e.target.value)}
          className="w-full h-8 rounded-md border border-input bg-transparent px-2.5 text-[13px] text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          {SCHEDULE_PRESETS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>

      {/* Custom: Date & Time Picker */}
      {preset === 'custom' && (
        <div className="grid grid-cols-2 gap-2">
          {/* Date Picker */}
          <div>
            <label className="text-[11px] font-medium text-muted-foreground block mb-1.5">Date</label>
            <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
              <PopoverTrigger
                className={cn(
                  "w-full h-8 rounded-md border border-input bg-transparent px-2.5 text-[13px] text-left flex items-center gap-2",
                  "hover:bg-accent hover:text-accent-foreground cursor-pointer",
                  !selectedDate && "text-muted-foreground"
                )}
              >
                <CalendarIcon className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                {selectedDate ? format(selectedDate, 'MMM d, yyyy') : 'Pick a date'}
              </PopoverTrigger>
              <PopoverContent align="start" className="w-auto p-0">
                <Calendar
                  selected={selectedDate}
                  onSelect={handleDateSelect}
                  disabled={(date) => date < new Date(new Date().setHours(0, 0, 0, 0))}
                />
              </PopoverContent>
            </Popover>
          </div>

          {/* Time Picker */}
          <div>
            <label className="text-[11px] font-medium text-muted-foreground block mb-1.5">Time</label>
            <div className="relative">
              <Clock3 className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
              <input
                type="time"
                value={timeValue}
                onChange={(e) => handleTimeChange(e.target.value)}
                className="w-full h-8 rounded-md border border-input bg-transparent pl-8 pr-2.5 text-[13px] text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>
        </div>
      )}

      {/* Timezone Selector */}
      <div>
        <label className="text-[11px] font-medium text-muted-foreground block mb-1.5">Timezone</label>
        <div className="relative">
          <Globe className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none z-10" />
          <select
            value={tz}
            onChange={(e) => handleTimezoneChange(e.target.value)}
            className="w-full h-8 rounded-md border border-input bg-transparent pl-8 pr-2.5 text-[13px] text-foreground focus:outline-none focus:ring-2 focus:ring-ring appearance-none"
          >
            {TIMEZONES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Next Run Display */}
      {nextRunAt && (
        <div className="rounded-lg bg-muted/50 px-3 py-2 text-[12px] text-muted-foreground">
          <span className="font-medium">Next run:</span>{' '}
          {new Date(nextRunAt).toLocaleString(undefined, { timeZone: tz, dateStyle: 'medium', timeStyle: 'short' })}
        </div>
      )}
    </div>
  );
}
