import fs from 'fs';
import path from 'path';

const repoDir = path.join(process.cwd(), 'public', 'agency-agents');
const outputFilePath = path.join(process.cwd(), 'public', 'agency-skills.json');

const skills = [];
const categories = new Set();
function extractFrontmatter(content) {
  if (!content.startsWith('---')) return { name: null, description: null };
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return { name: null, description: null };

  const frontmatter = match[1];
  const nameMatch = frontmatter.match(/^name:\s*(.+)$/im);
  const descMatch = frontmatter.match(/^description:\s*(.+)$/im);
  return {
    name: nameMatch ? nameMatch[1].trim().replace(/^['"]|['"]$/g, '') : null,
    description: descMatch ? descMatch[1].trim().replace(/^['"]|['"]$/g, '') : null,
  };
}

function walkSkills(dirPath) {
  if (!fs.existsSync(dirPath)) return;
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });

  for (const entry of entries) {
    if (entry.name.startsWith('.')) continue;
    const fullPath = path.join(dirPath, entry.name);

    if (entry.isDirectory()) {
      walkSkills(fullPath);
      continue;
    }

    if (!entry.isFile() || !entry.name.endsWith('.md') || entry.name === 'README.md') {
      continue;
    }

    const rel = path.relative(repoDir, fullPath).split(path.sep).join('/');
    const category = rel.split('/')[0] || 'misc';
    const fileBase = path.basename(entry.name, '.md');
    const content = fs.readFileSync(fullPath, 'utf-8');
    const { name, description } = extractFrontmatter(content);

    categories.add(category);
    skills.push({
      id: rel.replace(/\.md$/i, '').replace(/\//g, '--'),
      category,
      name: name || fileBase,
      description: description || '',
      publisher: 'Agency Agents',
      path: `/agency-agents/${rel}`,
    });
  }
}

walkSkills(repoDir);
skills.sort((a, b) => a.category.localeCompare(b.category) || a.name.localeCompare(b.name));

fs.writeFileSync(outputFilePath, JSON.stringify(skills, null, 2));
console.log(`Generated agency-skills.json with ${skills.length} skills across ${categories.size} categories.`);
