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
      sector_code: "G",
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

test("온보딩이 verify-biz 후 register로 이어지고 대시보드로 이동한다", async ({
  page,
}) => {
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
            name: "홍길동",
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
      tax_type: null,
      error_code: null,
    });
  });

  await page.route(`${API_BASE}/onboarding/register`, async (route) => {
    registerCalled = true;
    await fulfillApi(route, {
      biz_id: "biz-002",
      biz_name: "새로온 가게",
      biz_no: "1234567890",
      is_manual: false,
      profile_score: 55,
    });
  });

  await page.goto("/onboarding");
  await page.getByTestId("onboarding-biz-name").fill("새로온 가게");
  await page.getByTestId("onboarding-biz-no").fill("123-45-67890");
  await page.locator("#ob-industry").fill("도매");
  await page.locator("#ob-industry").press("ArrowDown");
  await page.locator("#ob-industry").press("Enter");
  await page.locator("#ob-region-sido").selectOption("11");
  await page.getByTestId("onboarding-region-sigungu").fill("강남구");
  await page.getByTestId("onboarding-employee-count").fill("3");
  await page.getByTestId("onboarding-submit").click();

  await expect.poll(() => verifyCalled).toBeTruthy();
  await expect.poll(() => registerCalled).toBeTruthy();
  await expect(page).toHaveURL(/\/dashboard$/);
});
