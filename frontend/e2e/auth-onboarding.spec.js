import { test, expect } from "@playwright/test";

const API_BASE = "http://localhost:8000/api/v1";

async function fulfillApi(route, body, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify({
      status: "success",
      message: "ok",
      data: body,
    }),
  });
}

async function mockDashboardApis(page) {
  await page.route(`${API_BASE}/businesses/me`, async (route) => {
    await fulfillApi(route, {
      biz_id: "biz-001",
      biz_name: "데모 상점",
      biz_no: "1234567890",
      sector_code: "RETAIL",
    });
  });

  await page.route(`${API_BASE}/policies/recommend*`, async (route) => {
    await fulfillApi(route, { items: [] });
  });

  await page.route(`${API_BASE}/diagnoses`, async (route) => {
    await fulfillApi(route, []);
  });

  await page.route(`${API_BASE}/documents`, async (route) => {
    await fulfillApi(route, []);
  });
}

test("테스트 계정 로그인 후 대시보드로 이동한다", async ({ page }) => {
  await mockDashboardApis(page);

  await page.route(`${API_BASE}/auth/test-login`, async (route) => {
    await fulfillApi(route, {
      access_token: "access-token",
      refresh_token: "refresh-token",
      user_id: "user-001",
      is_new_user: false,
    });
  });

  await page.goto("/login?callbackUrl=%2Fdashboard");
  await page.getByTestId("test-login-input").fill("demo-owner");
  await page.getByTestId("test-login-submit").click();

  await expect(page).toHaveURL(/\/dashboard$/);
});

test("온보딩이 verify-biz 후 register로 이어지고 대시보드로 이동한다", async ({ page }) => {
  let verifyCalled = false;
  let registerCalled = false;

  await page.addInitScript(() => {
    window.localStorage.setItem(
      "biz_up_auth",
      JSON.stringify({
        state: {
          accessToken: "access-token",
          refreshToken: "refresh-token",
          user: {
            userId: "user-002",
            provider: "kakao",
            isOnboarded: false,
            name: "신규 사용자",
          },
          hasHydrated: true,
        },
        version: 0,
      })
    );
  });

  await mockDashboardApis(page);

  await page.route(`${API_BASE}/onboarding/verify-biz`, async (route) => {
    verifyCalled = true;
    await fulfillApi(route, {
      is_valid: true,
      biz_status: "계속사업자",
      error_code: null,
    });
  });

  await page.route(`${API_BASE}/onboarding/register`, async (route) => {
    registerCalled = true;
    await fulfillApi(route, {
      biz_id: "biz-002",
      biz_name: "새로운 가게",
      biz_no: "1234567890",
    });
  });

  await page.goto("/onboarding");
  await page.getByTestId("onboarding-biz-name").fill("새로운 가게");
  await page.getByTestId("onboarding-biz-no").fill("123-45-67890");
  await page.locator("#ob-industry").fill("소매");
  await page.locator("#ob-industry").press("ArrowDown");
  await page.locator("#ob-industry").press("Enter");
  await page.getByTestId("onboarding-employee-count").fill("3");
  await page.getByTestId("onboarding-submit").click();

  await expect.poll(() => verifyCalled).toBeTruthy();
  await expect.poll(() => registerCalled).toBeTruthy();
  await expect(page).toHaveURL(/\/dashboard$/);
});
