import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, parseISO } from 'date-fns';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatIDR(amount: number): string {
  const absAmount = Math.abs(amount);
  const formatted = absAmount
    .toFixed(0)
    .replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const prefix = amount < 0 ? '-Rp ' : 'Rp ';
  return `${prefix}${formatted}`;
}

export function formatPercent(value: number): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export function formatDate(date: string): string {
  try {
    const parsed = parseISO(date);
    return format(parsed, 'dd MMM yyyy');
  } catch {
    return date;
  }
}

export function formatNumber(n: number): string {
  return n.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}
