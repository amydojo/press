export type ApiErrorKind =
  | "network_error"
  | "http_error"
  | "malformed_response";

export class PressApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly statusCode?: number;

  constructor(kind: ApiErrorKind, message: string, statusCode?: number) {
    super(message);
    this.name = "PressApiError";
    this.kind = kind;
    this.statusCode = statusCode;
  }
}
