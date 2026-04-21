import apiClient from "@/lib/api-client";
import type {
  SocialAuthRequest,
  SocialLoginResponseData,
  TestLoginRequest,
} from "@/types";

export const authService = {
  socialLogin: (body: SocialAuthRequest) =>
    apiClient.post<SocialLoginResponseData>("/auth/social-login", body),
  testLogin: (body: TestLoginRequest) =>
    apiClient.post<SocialLoginResponseData>("/auth/test-login", body),
};
