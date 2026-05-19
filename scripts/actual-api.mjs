#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const api = require('/Users/bj/.openclaw/actual-budget-server/node_modules/@actual-app/api');

const BASE = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const CONFIG = path.join(BASE, 'config', 'actual-budget.json');
const DEFAULT_START_DAYS = 45;
const AUTO_CATEGORY_DAYS = 370;

function dollars(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return null;
  return Math.round((value / 100) * 100) / 100;
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoISO(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function monthISO() {
  return new Date().toISOString().slice(0, 7);
}

function displayPayee(t) {
  return t.imported_payee || t.payee_name || t.payee || '';
}

function normalize(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

async function loadConfig() {
  const raw = await fs.readFile(CONFIG, 'utf8');
  return JSON.parse(raw);
}

async function connect() {
  const cfg = await loadConfig();
  let filePassword = '';
  if (cfg.password_file) {
    try {
      filePassword = (await fs.readFile(cfg.password_file, 'utf8')).trim();
    } catch {
      filePassword = '';
    }
  }
  const password = process.env.ACTUAL_PASSWORD || filePassword || cfg.password;
  if (!password) {
    throw new Error('ACTUAL_PASSWORD is not set. Set it in the environment; do not store bank credentials in project files.');
  }
  if (!cfg.sync_id) {
    throw new Error('config/actual-budget.json is missing sync_id.');
  }
  const dataDir = process.env.ACTUAL_API_CACHE_DIR || cfg.api_cache_dir || '/Users/bj/.openclaw/actual-budget-api-cache';
  await fs.mkdir(dataDir, { recursive: true });
  await api.init({
    dataDir,
    serverURL: cfg.server_url || 'http://127.0.0.1:5006',
    password,
  });
  await api.downloadBudget(cfg.sync_id);
  return cfg;
}

async function safeShutdown() {
  try {
    await api.shutdown();
  } catch {
    // no-op
  }
}

async function collectSummary() {
  const accounts = await api.getAccounts();
  const categories = await api.getCategories();
  const categoriesById = new Map();
  for (const category of categories) {
    if (category.id) {
      categoriesById.set(category.id, category.name);
    }
  }
  const month = await api.getBudgetMonth(monthISO()).catch(() => null);
  const start = daysAgoISO(DEFAULT_START_DAYS);
  const end = todayISO();
  const transactions = [];
  for (const account of accounts) {
    if (account.closed) continue;
    const rows = await api.getTransactions(account.id, start, end).catch(() => []);
    for (const row of rows) {
      transactions.push({ ...row, account_name: account.name });
    }
  }
  const uncategorized = transactions
    .filter(t => !t.category && !t.is_parent && !t.transfer_id)
    .sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')));
  const recent = transactions
    .sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')))
    .slice(0, 30);
  return {
    generated_at: new Date().toISOString(),
    budget_month: monthISO(),
    accounts: await Promise.all(accounts.map(async a => ({
      id: a.id,
      name: a.name,
      offbudget: !!a.offbudget,
      closed: !!a.closed,
      balance: dollars(await api.getAccountBalance(a.id).catch(() => a.balance_current ?? a.balance ?? 0)),
    }))),
    category_count: categories.length,
    categories: categories.map(c => ({
      id: c.id,
      name: c.name,
      group: c.group,
      is_group: !!(c.is_group || c.categories),
      hidden: !!c.hidden,
    })),
    category_groups: categories.filter(c => c.is_group || c.categories).map(c => ({
      id: c.id,
      name: c.name,
      hidden: !!c.hidden,
    })),
    month: month ? {
      income_available: dollars(month.incomeAvailable),
      total_budgeted: dollars(month.totalBudgeted),
      total_spent: dollars(month.totalSpent),
      total_balance: dollars(month.totalBalance),
      to_budget: dollars(month.toBudget),
    } : null,
    transaction_window: { start, end, count: transactions.length },
    uncategorized_count: uncategorized.length,
    uncategorized: uncategorized.slice(0, 12).map(t => ({
      id: t.id,
      date: t.date,
      account: t.account_name,
      payee: displayPayee(t),
      notes: t.notes || '',
      amount: dollars(t.amount),
      imported_payee: t.imported_payee || '',
    })),
    recent: recent.slice(0, 12).map(t => ({
      id: t.id,
      date: t.date,
      account: t.account_name,
      payee: displayPayee(t),
      category: t.category_name || categoriesById.get(t.category) || t.category || '',
      notes: t.notes || '',
      amount: dollars(t.amount),
    })),
  };
}

async function collectTransactions(days = AUTO_CATEGORY_DAYS) {
  const accounts = await api.getAccounts();
  const start = daysAgoISO(days);
  const end = todayISO();
  const transactions = [];
  for (const account of accounts) {
    if (account.closed) continue;
    const rows = await api.getTransactions(account.id, start, end).catch(() => []);
    for (const row of rows) {
      transactions.push({ ...row, account_name: account.name });
    }
  }
  return { start, end, transactions };
}

function categoryMap(categories) {
  const map = new Map();
  for (const c of categories) {
    if (c.categories) continue;
    map.set(normalize(c.name), c);
  }
  return map;
}

function categoryByName(categoriesByName, name) {
  return categoriesByName.get(normalize(name)) || null;
}

const AUTO_CATEGORY_RULES = [
  { category: 'Electric', any: ['central maine power', 'cmpco', 'cmp '] },
  { category: 'Phone / Internet', any: ['spectrum', 'verizon', 't mobile', 'tmobile', 'xfinity', 'comcast'] },
  { category: 'Subscriptions', any: ['netflix', 'hulu', 'spotify', 'patreon', 'substack', 'simplefin bridge'] },
  { category: 'Apps / Tools', any: ['apple', 'openai', 'anthropic', 'github', 'google storage', 'google one', 'canva', 'namecheap', 'hover', 'replit'] },
  { category: 'Groceries', any: ['hannaford', 'belfast community', 'walmart', 'target', 'trader joe', 'whole foods', 'market basket', 'shaw s', 'food'] },
  { category: 'Dining Out', any: ['doordash', 'uber eats', 'mcdonald', 'burger king', 'subway', 'dunkin', 'starbucks', 'pizza', 'restaurant', 'cafe'] },
  { category: 'Coffee / Snacks', any: ['cumberland farms', 'circle k', 'irving', '7 eleven', 'convenience'] },
  { category: 'Nicotine / Tobacco', any: ['cigaret', 'cigarette', 'smoke shop', 'tobacco'] },
  { category: 'Gas / Transit', any: ['shell', 'sunoco', 'mobil', 'exxon', 'citgo', 'gas', 'fuel', 'parking'] },
  { category: 'Medical', any: ['doctor', 'hospital', 'clinic', 'urgent care', 'quest diagnostic', 'labcorp', 'mainehealth'] },
  { category: 'Medication', any: ['walgreens', 'cvs pharmacy', 'rite aid', 'pharmacy'] },
  { category: 'Therapy', any: ['therapy', 'therapist', 'counseling', 'psychology'] },
  { category: 'Fitness / Movement', any: ['planet fitness', 'ymca', 'gym'] },
  { category: 'Rent / Housing', any: ['rent', 'landlord', 'property management'] },
  { category: 'Insurance', any: ['insurance', 'geico', 'progressive', 'state farm'] },
  { category: 'Cash / ATM', any: ['atm withdrawal', 'atm '] },
  { category: 'Loans', any: ['loan pay', 'stmarys', 'st marys', 'student loan'] },
  { category: 'Credit Cards', any: ['credit card payment', 'card payment', 'capital one', 'discover'] },
  { category: 'Books / Learning', any: ['bookshop', 'barnes noble', 'audible', 'kindle', 'udemy'] },
  { category: 'Doobaleedoos', any: ['youtube', 'vidiq', 'epidemic sound', 'artlist'] },
];

function chooseCategory(transaction, { fallbackCategory = 'General' } = {}) {
  const payee = normalize(displayPayee(transaction));
  const notes = normalize(transaction.notes);
  const haystack = `${payee} ${notes}`;
  if (Number(transaction.amount || 0) > 0) {
    return 'Income';
  }
  for (const rule of AUTO_CATEGORY_RULES) {
    if (rule.any.some(term => haystack.includes(normalize(term)))) {
      return rule.category;
    }
  }
  return fallbackCategory;
}

async function autoCategorize({ dryRun = false, fallbackCategory = 'General' } = {}) {
  const categories = await api.getCategories();
  const byName = categoryMap(categories);
  const { start, end, transactions } = await collectTransactions(AUTO_CATEGORY_DAYS);
  const uncategorized = transactions
    .filter(t => !t.category && !t.is_parent && !t.transfer_id)
    .sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')));

  const planned = [];
  const skipped = [];
  for (const transaction of uncategorized) {
    const categoryName = chooseCategory(transaction, { fallbackCategory });
    const category = categoryByName(byName, categoryName);
    if (!category) {
      skipped.push({
        id: transaction.id,
        date: transaction.date,
        payee: displayPayee(transaction),
        amount: dollars(transaction.amount),
        reason: `missing category: ${categoryName}`,
      });
      continue;
    }
    planned.push({
      id: transaction.id,
      date: transaction.date,
      account: transaction.account_name,
      payee: displayPayee(transaction),
      amount: dollars(transaction.amount),
      category: categoryName,
      category_id: category.id,
    });
  }

  const changed = [];
  if (!dryRun) {
    for (const item of planned) {
      await api.updateTransaction(item.id, { category: item.category_id });
      changed.push(item);
    }
    if (changed.length) {
      await api.sync();
    }
  }

  return {
    generated_at: new Date().toISOString(),
    dry_run: dryRun,
    window: { start, end },
    uncategorized_seen: uncategorized.length,
    categorized_count: dryRun ? 0 : changed.length,
    planned_count: planned.length,
    skipped_count: skipped.length,
    sample: (dryRun ? planned : changed).slice(0, 20).map(({ category_id, ...item }) => item),
    skipped: skipped.slice(0, 20),
    fallback_category: fallbackCategory,
  };
}

const GIMBLE_CATEGORY_GROUPS = [
  {
    name: 'Monthly Bills',
    categories: ['Rent / Housing', 'Electric', 'Phone / Internet', 'Insurance', 'Subscriptions', 'Other Bills'],
  },
  {
    name: 'Everyday Spending',
    categories: ['Groceries', 'Dining Out', 'Coffee / Snacks', 'Nicotine / Tobacco', 'Gas / Transit', 'Household', 'Cash / ATM'],
  },
  {
    name: 'Care & Health',
    categories: ['Medical', 'Medication', 'Therapy', 'Supplements', 'Fitness / Movement'],
  },
  {
    name: 'Savings & Future',
    categories: ['Emergency Fund', 'Car / Repairs', 'Taxes / Fees', 'Buffer'],
  },
  {
    name: 'Wonder & Work',
    categories: ['Doobaleedoos', 'Tiny Adventures', 'Books / Learning', 'Apps / Tools'],
  },
  {
    name: 'Debt & Tethers',
    categories: ['Loans', 'Credit Cards', 'Debt Extra Payments'],
  },
];

async function setupGimbleCategories() {
  const beforeGroups = await api.getCategoryGroups();
  const beforeCategories = await api.getCategories();
  const existingGroups = new Map(beforeGroups.map(c => [c.name.toLowerCase(), c]));
  const existingCategories = new Set(beforeCategories.filter(c => !c.categories).map(c => c.name.toLowerCase()));
  const created = [];
  for (const group of GIMBLE_CATEGORY_GROUPS) {
    let groupId = existingGroups.get(group.name.toLowerCase())?.id;
    if (!groupId) {
      groupId = await api.createCategoryGroup({ name: group.name, is_income: false, hidden: false });
      created.push({ type: 'group', name: group.name, id: groupId });
    }
    for (const name of group.categories) {
      if (existingCategories.has(name.toLowerCase())) continue;
      const id = await api.createCategory({ name, group_id: groupId, is_income: false, hidden: false });
      existingCategories.add(name.toLowerCase());
      created.push({ type: 'category', group: group.name, name, id });
    }
  }
  await api.sync();
  return { created, total_created: created.length };
}

async function main() {
  const command = process.argv[2] || 'summary';
  try {
    await connect();
    if (command === 'summary') {
      console.log('__ACTUAL_JSON_START__');
      console.log(JSON.stringify(await collectSummary(), null, 2));
      console.log('__ACTUAL_JSON_END__');
    } else if (command === 'accounts') {
      console.log('__ACTUAL_JSON_START__');
      console.log(JSON.stringify(await api.getAccounts(), null, 2));
      console.log('__ACTUAL_JSON_END__');
    } else if (command === 'categories') {
      console.log('__ACTUAL_JSON_START__');
      console.log(JSON.stringify(await api.getCategories(), null, 2));
      console.log('__ACTUAL_JSON_END__');
    } else if (command === 'bank-sync') {
      const accounts = await api.getAccounts();
      const results = [];
      for (const account of accounts.filter(a => !a.closed)) {
        try {
          await api.runBankSync({ accountId: account.id });
          results.push({ account: account.name, ok: true });
        } catch (error) {
          results.push({ account: account.name, ok: false, error: String(error?.message || error) });
        }
      }
      console.log('__ACTUAL_JSON_START__');
      console.log(JSON.stringify({ generated_at: new Date().toISOString(), results }, null, 2));
      console.log('__ACTUAL_JSON_END__');
    } else if (command === 'auto-categorize') {
      const dryRun = process.argv.includes('--dry-run');
      const fallbackArg = process.argv.find(arg => arg.startsWith('--fallback='));
      const fallbackCategory = fallbackArg ? fallbackArg.split('=').slice(1).join('=') : 'General';
      console.log('__ACTUAL_JSON_START__');
      console.log(JSON.stringify(await autoCategorize({ dryRun, fallbackCategory }), null, 2));
      console.log('__ACTUAL_JSON_END__');
    } else if (command === 'setup-gimble-categories') {
      console.log('__ACTUAL_JSON_START__');
      console.log(JSON.stringify(await setupGimbleCategories(), null, 2));
      console.log('__ACTUAL_JSON_END__');
    } else {
      throw new Error(`Unknown command: ${command}`);
    }
  } finally {
    await safeShutdown();
  }
}

main().catch(err => {
  console.error(err?.stack || err?.message || String(err));
  process.exit(1);
});
