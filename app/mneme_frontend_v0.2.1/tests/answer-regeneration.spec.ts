import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.clear());
  await page.goto('/?preview=1', { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: 'AI Laboratory', exact: true }).click();
});

test('restores an explicit mode and regenerates with run metadata on desktop and mobile', async ({ page }) => {
  const modes = page.getByRole('radiogroup', { name: 'Answer mode' });
  const memoryMode = modes.getByRole('radio', { name: 'Long-term memory' });
  await memoryMode.click();
  await expect(memoryMode).toHaveAttribute('aria-checked', 'true');

  const existingAnswer = page.getByText('Start with the indexed documents').locator('..');
  await expect(existingAnswer.getByText(/Run run-preview-existing/)).toBeVisible();
  await expect(existingAnswer.getByText(/document/).first()).toBeVisible();
  await existingAnswer.getByRole('button', { name: 'Regenerate in selected mode' }).click();

  await expect(page.getByText('Preview answer for: How should I review this vault?').last()).toBeVisible();
  await expect(page.getByText(/Run run-preview-/).last()).toBeVisible();
  await expect(page.getByText('Long-term memory').last()).toBeVisible();

  await expect(memoryMode).toHaveAttribute('aria-checked', 'true');
});
