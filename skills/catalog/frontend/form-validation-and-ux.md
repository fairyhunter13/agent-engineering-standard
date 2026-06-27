---
name: form-validation-and-ux
description: Build accessible, low-abandonment forms with inline validation, schema-driven error messages, and persistent state.
discipline: frontend
tags: [forms, validation, ux, accessibility, react-hook-form]
---

# Form Validation and UX

## When to use
Apply this skill when building any data-entry form (registration, checkout, settings, search filters); when forms have high abandonment rates; when an accessibility audit flags form errors; or when users report losing input data on navigation or error.

## Signal
- Validation only fires on submit — no inline feedback while filling out the form.
- Error messages are displayed but not associated with their input field (not announced by screen readers).
- Users lose all entered data when a submit error occurs (uncontrolled form reset).
- No client-side validation — every validation requires a round-trip to the server.
- Submit button is disabled before the user has interacted, causing confusion about why it is inactive.
- `required` attribute present but no visible indicator of which fields are required.
- Errors placed only at the top of the form, not adjacent to the offending field.

## Why
Poor form validation is a primary cause of form abandonment. Server-round-trip-only validation wastes latency and creates jarring UX on every mistake. Inaccessible error messages (not linked to their inputs) fail WCAG 1.3.1 (Info and Relationships) and WCAG 3.3.1 (Error Identification), creating legal risk. Losing user input on a failed submission is one of the most damaging UX failures possible — users may give up entirely.

## Remediate

1. **Use `react-hook-form` + `zod` as the standard stack.** `react-hook-form` is performant (uncontrolled inputs, minimal re-renders) and `zod` provides TypeScript-safe schema validation shared between client and server:
   ```ts
   const schema = z.object({
     email: z.string().email('Enter a valid email address'),
     password: z.string().min(8, 'Password must be at least 8 characters'),
   });
   const { register, handleSubmit, formState: { errors } } = useForm({
     resolver: zodResolver(schema),
   });
   ```

2. **Validate on blur for each field, revalidate on submit.** Showing errors while the user types is disruptive. Validate when focus leaves the field (`mode: 'onBlur'` in `react-hook-form`). On submit, revalidate all fields and focus the first error.

3. **Show inline errors immediately beneath each field.** Errors must appear directly under the field they relate to — not only at the top of the form. Use `aria-describedby` to link the error message to the input:
   ```tsx
   <input
     id="email"
     {...register('email')}
     aria-describedby={errors.email ? 'email-error' : undefined}
     aria-invalid={!!errors.email}
   />
   {errors.email && (
     <p id="email-error" role="alert" className="error-message">
       {errors.email.message}
     </p>
   )}
   ```

4. **Preserve form state across navigation and errors.** Use uncontrolled inputs (default in `react-hook-form`) so browser native behavior preserves values. For multi-step forms or forms where navigation away is common, persist state in `sessionStorage`:
   ```ts
   const saved = JSON.parse(sessionStorage.getItem('checkout-form') ?? '{}');
   useForm({ defaultValues: saved });
   ```

5. **Handle submit-button state carefully.** Disable the submit button only after the first submit attempt when there are errors — not before the user interacts. Pre-disabling a button gives no indication of *why* it is disabled. Use `formState.isSubmitting` to disable during in-flight submission:
   ```tsx
   <button type="submit" disabled={isSubmitting}>
     {isSubmitting ? 'Saving...' : 'Save'}
   </button>
   ```

6. **Mark required fields clearly.** Indicate required fields with a visible marker (asterisk) and a legend: "* Required fields". Use `aria-required="true"` on custom inputs or `required` on native inputs. Never rely solely on placeholder text as a label.

7. **Write clear, actionable error messages.** Avoid generic messages like "Invalid input." Be specific: "Enter a valid email address (example: name@domain.com)". Provide the corrective action, not just the failure.

8. **Prevent double-submission.** Disable the submit button or track `isSubmitting` state to prevent duplicate API calls from impatient users clicking multiple times.

9. **Test with keyboard and screen reader.** Tab through the form completely. Verify that error messages are announced when focus lands on the field or when `role="alert"` content is injected. Test with VoiceOver (Safari/macOS) and NVDA (Firefox/Windows).

10. **Server-side validation is still required.** Client validation is a UX enhancement, not a security measure. Always validate and sanitize on the server; never trust client-provided data.

## References
- react-hook-form documentation (react-hook-form.com)
- Zod documentation (zod.dev)
- WCAG 3.3 Input Assistance success criteria
- Gov.uk Design System — Error messages patterns
