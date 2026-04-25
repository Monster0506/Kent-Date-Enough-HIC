#set document(
  title: "Kent Date Enough: HIC Final Report",
  author: "Sumedh Joshi, Logan Senol, Mason Bair, Emmanuel Uka, TJ Raklovits",
)

#set page(
  paper: "us-letter",
  margin: (top: 1in, bottom: 1in, left: 1in, right: 1in),
  numbering: "1",
  number-align: right,
  header: context {
    if counter(page).get().first() > 1 {
      grid(
        columns: (1fr, 1fr),
        align(left)[#text(size: 9pt, fill: gray)[Kent Date Enough]],
        align(right)[#text(size: 9pt, fill: gray)[Sumedh Joshi, Logan Senol, Mason Bair, Emmanuel Uka, TJ Raklovits]],
      )
      line(length: 100%, stroke: 0.5pt + gray)
    }
  },
)

#set text(font: ("New Computer Modern", "Libertinus Serif"), size: 11pt, lang: "en")
#set heading(numbering: "1.1")
#set par(justify: true, leading: 0.75em)

#show heading.where(level: 1): it => {
  v(1.2em)
  text(size: 16pt, weight: "bold")[#it]
  v(0.4em)
}
#show heading.where(level: 2): it => {
  v(0.9em)
  text(size: 13pt, weight: "bold")[#it]
  v(0.3em)
}
#show heading.where(level: 3): it => {
  v(0.6em)
  text(size: 11pt, weight: "semibold", style: "italic")[#it]
  v(0.2em)
}

#let rule(name) = [
  #v(0.4em)
  #box(
    fill: rgb("#023672"),
    inset: (x: 5pt, y: 2pt),
    radius: 3pt,
    text(fill: white, size: 8.5pt, weight: "bold")[#name],
  )
  #v(0.15em)
]

#let screenshot(path, caption) = {
  v(0.4em)
  figure(
    image(path, width: 100%),
    caption: caption,
  )
  v(0.4em)
}

#align(center)[
  #v(2in)
  #text(size: 28pt, weight: "bold")[Kent Date Enough]
  #v(0.4em)
  #text(size: 16pt, fill: rgb("#023672"))[Human Interface Computing Final Report]
  #v(2em)
  #line(length: 60%, stroke: 1.5pt + rgb("#EAAB00"))
  #v(2em)
  #text(size: 12pt)[Sumedh Joshi · Logan Senol · Mason Bair · Emmanuel Uka · TJ Raklovits]
  #v(0.5em)
  #text(size: 11pt, fill: gray)[Kent State University]
  #v(0.5em)
  #text(size: 11pt, fill: gray)[Spring 2026]
]

#pagebreak()

#outline(
  title: [Table of Contents],
  depth: 2,
  indent: 1.5em,
)

#pagebreak()

= Platform Overview

== Description and Purpose

Kent Date Enough is a college dating web application built specifically for
students at Kent State University. Its core purpose is to help students
discover romantic or social connections with peers who share their academic
life: the same classes, major, year of study, or compatible free periods
between lectures.

Unlike general-purpose dating apps, Kent Date Enough integrates directly with
the university's Banner course registration system. Users enter their Class
Registration Numbers (CRNs) and the app fetches their full course schedule
automatically. This schedule data powers a compatibility scoring algorithm that
rewards profiles who share classes or overlapping free time, making it far more
likely that two matched users will meet organically on campus. Each match also
receives an AI-generated icebreaker from the Google Gemini API that references
the pair's shared courses, lowering the barrier to a first conversation.

The platform offers the following core functionality:

- *Account creation and authentication*: students create a personal account
  secured with PBKDF2-HMAC-SHA256 hashed passwords.
- *Profile building*: users fill in name, pronouns, major, year, height, age,
  a profile photo, and a comma-separated traits section.
- *Schedule integration*: users enter CRNs; the app scrapes Kent State's
  Banner system (term 202610) and stores full course details.
- *Discover (swipe) interface*: one ranked candidate is shown at a time;
  the user accepts or rejects them. Arrow-key shortcuts allow rapid browsing.
- *Matching and messaging*: a mutual acceptance creates a match and opens a
  private chat. Every chat opens with a streamed, AI-generated icebreaker.
- *Notifications*: new matches, unread messages, and profile-completeness
  nudges are surfaced automatically with a badge counter in the navigation.
- *Settings*: users filter matches by gender preference, age range, and
  whether major must align.
- *Testimonials*: a public community board for sharing success stories.
- *Reporting*: users can flag inappropriate profiles from the Discover card
  or the full-profile view.

The application is built with Python (Kindling framework made by TJ), Jinja2
HTML templates, Tailwind CSS for styling, SQLite for data persistence, and the
Google Gemini API for icebreaker generation.

= Pages and Screens

The sections below describe every distinct page in the application. For each
page the following are covered:

1. *Purpose*: why the page exists.
2. *Screenshot*: a captured screenshot of the live application.
3. *Golden Rules*: which of Shneiderman's Eight Golden Rules apply and how.
4. *User Interactions*: what the user can do on the page.

== Landing Page (`/`)

=== Purpose

The landing page is the first screen unauthenticated visitors see. Its sole
job is to communicate what the platform is and to direct the user toward either
creating an account or logging into an existing one. It contains no forms and
no authenticated content.

=== Screenshot

#screenshot("screenshots/01-landing.png", "Landing page: title, tagline, and the two entry-point buttons.")

=== Golden Rules

#rule("Strive for Consistency")
The landing page establishes the full visual language of the application:
brand blue, accent yellow, cream card backgrounds, and the Jura display
typeface. Every subsequent page inherits this palette and typography, so
returning users are immediately oriented regardless of which page they land on.

#rule("Reduce Short-Term Memory Load")
The entire decision space fits on one screen: two clearly labelled buttons,
"Log In" and "Sign Up". There is nothing to remember, no sub-menu to navigate.
The tagline "Find a lover in a flash" communicates the purpose of the platform
in a single phrase.

#rule("Support Internal Locus of Control")
The interface is fully passive until the user acts. Neither button triggers any
automatic action; the application waits for the user to choose their path.

=== User Interactions

- Click *Log In* to navigate to the login page.
- Click *Sign Up* to navigate to account creation.
- No forms, no authentication state, all interactions are simple navigations.

== Sign Up Page (`/signup`)

=== Purpose

The sign-up page allows a new visitor to create a Kent Date Enough account. It
collects a username and password (confirmed twice) and, on success, creates the
account along with a default `user_settings` row before presenting a
confirmation screen that links to login.

=== Screenshot

#screenshot("screenshots/02-signup.png", "Sign-up page: username, password, and confirm-password fields.")

=== Golden Rules

#rule("Offer Informative Feedback")
As the user types in the Confirm Password field, the field border changes
colour in real time: gold when both passwords match, red when they diverge.
This live validation means the user learns of a mismatch immediately, without
waiting for a round-trip to the server. Server-side errors (username already
taken, password too short) are then displayed inline, directly below the form.

#rule("Offer Simple Error Handling")
All validation errors appear as plain-English messages. The form retains the
username value so only the failing field needs correction. To prevent
double-submissions, which would produce confusing duplicate-account errors. The
submit button is disabled as soon as the form is submitted and re-enables only
if an error is returned.

#rule("Design Dialogue to Yield Closure")
After a successful creation the page shows a confirmation screen ("Account
created! Log in now") so the user knows the three-step flow (fill form →
submit → confirm) has reached its natural end before they move on.

#rule("Strive for Consistency")
The cream card on a slate border, the brand-yellow submit button, and the Jura
heading are identical to those on the login page, forming a visual pair that
signals these are the two sides of the same authentication gate.

#rule("Reduce Short-Term Memory Load")
Password requirements (minimum 6 characters, must match) are enforced through
live visual feedback and inline error copy rather than a static notice the user
must remember to consult.

=== User Interactions

- Enter a *username* (must be unique across all accounts).
- Enter a *password* (minimum 6 characters).
- Re-enter the password in *Confirm Password*, the field border updates live
  to indicate match or mismatch.
- Click *Sign Up* (or press Enter) to submit.
- On success: a confirmation screen appears with a link to the login page.
- On failure: inline error messages describe the problem; correct and resubmit.

// ─────────────────────────────────────────────────────────────────────────────
== Login Page (`/login`)
// ─────────────────────────────────────────────────────────────────────────────

=== Purpose

The login page authenticates returning users. It verifies the submitted
username and password against the stored PBKDF2-HMAC-SHA256 hash and, on
success, creates a session cookie and redirects to the Discover page.

=== Screenshot

#screenshot("screenshots/03-login.png", "Login page: username and password fields, Log In button, and sign-up link.")

=== Golden Rules

#rule("Strive for Consistency")
The card layout, colour scheme, and button style are identical to the sign-up
page. The two screens are visually paired, making it obvious they belong to the
same authentication flow.

#rule("Offer Informative Feedback")
Incorrect credentials produce a clear error message ("Invalid username or
password") displayed at the top of the card. The user is never left wondering
whether the problem was the username, the password, or the server.

#rule("Permit Easy Reversal of Actions")
A "Don't have an account? Sign up" link at the bottom of the card lets users
who arrived at the wrong page recover without resorting to the browser's Back
button.

#rule("Reduce Short-Term Memory Load")
Only two fields are required. Placeholder text reminds the user of what each
field expects. There are no CAPTCHA challenges or secondary factors that the
user must remember how to complete.

=== User Interactions

- Enter *username* and *password*.
- Click *Log In* (or press Enter) to authenticate.
- On success: redirected to `/discover`.
- On failure: inline error message; try again.
- Click *Sign up here* to navigate to account creation.

// ─────────────────────────────────────────────────────────────────────────────
== My Profile Page (`/profile`)
// ─────────────────────────────────────────────────────────────────────────────

=== Purpose

The profile page lets authenticated users build and edit their personal
profile: photo, name, pronouns, gender, major, year, height, age, and a
comma-separated traits section. This information appears on every profile card
shown to other users in the Discover feed and drives the compatibility scoring
algorithm, users with more complete profiles surface higher in other users'
feeds.

=== Screenshot

#screenshot("screenshots/05-profile.png", "My Profile: photo upload on the left, editable fields on the right.")

=== Golden Rules

#rule("Strive for Consistency")
The two-column layout (photo left, fields right) mirrors the visual structure
of the Settings and Chats pages. Dropdowns for Gender and Year use the same
`<select>` styling as every other dropdown in the application.

#rule("Offer Informative Feedback")
Selecting a new photo triggers an immediate live preview in the circular photo
area, no submit required. After saving, a toast notification appears
prominently above the form reading "Profile updated!", confirming the action.
This toast placement was deliberately chosen to ensure
it is visible without scrolling.

#rule("Permit Easy Reversal of Actions")
The page tracks a "dirty" state whenever a field value changes. If the user
tries to navigate away before saving, a browser confirmation dialog warns that
unsaved changes will be discarded. This guards against
accidental data loss from clicking a sidebar link mid-edit.

#rule("Offer Simple Error Handling")
Required fields (Name, Age) are enforced before submission with inline error
messages. Age is validated to be 18 or older. The Major field uses a
`<datalist>` populated with 40+ Kent State programmes, and
Height uses a datalist spanning 4'10" to 6'5", both
normalising free-text input so that matching and display remain consistent.

#rule("Reduce Short-Term Memory Load")
Autocomplete suggestions for Major and Height mean users do not need to recall
a specific format string. The photo preview area displays the current photo
whenever the page loads, so users always know what others will see.

=== User Interactions

- Click the *photo area* to open the file picker; the preview updates
  immediately on selection.
- Fill in *Name* and *Age* (required fields).
- Optionally fill in *Pronouns*, *Major* (autocomplete), *Year* (dropdown),
  *Height* (datalist), *Gender* (dropdown), and *Traits* (comma-separated).
- Click *Save* to persist changes; a success toast confirms the update.
- Navigating away with unsaved changes triggers a "discard changes?" dialog.

// ─────────────────────────────────────────────────────────────────────────────
== Discover Page (`/discover`)
// ─────────────────────────────────────────────────────────────────────────────

=== Purpose

The Discover page is the primary matching interface. One candidate profile is
shown at a time, ranked by a composite compatibility score, and the user
accepts or rejects the candidate. When two users have each accepted the other a
match is created and chat becomes available. The page intentionally presents
one profile at a time to focus the user's attention and prevent decision
paralysis.

=== Screenshot

#screenshot("screenshots/04-discover.png", "Discover: ranked profile card with compatibility badge, Accept and Reject buttons.")

=== Golden Rules

#rule("Strive for Consistency")
The Accept button is always green and positioned on the right; the Reject
button is always red and on the left. This spatial-colour convention never
changes across profiles, allowing users to build a reliable motor habit and
act quickly without reading button labels on each card. All other destructive
or irreversible actions in the application also use red buttons, reinforcing the same convention globally.

#rule("Enable Frequent Users to Use Shortcuts")
Arrow-key bindings were added explicitly for power users:
the *right arrow* accepts and the *left arrow* rejects. Users who swipe through
many profiles per session can do so entirely from the keyboard with no mouse
interaction required.

#rule("Offer Informative Feedback")
- A numeric compatibility score badge on each card shows how well the candidate
  aligns with the current user. Hovering the badge reveals a tooltip that breaks down the score components: shared CRNs, same major,
  same year, and overlapping free periods.
- A match toast ("It's a match with [Name]!") appears at the top of the page
  immediately after a mutual acceptance.
- An "Undo" notification bar appears at the bottom after each rejection,
  confirming the swipe was registered and offering a way to reverse it.
- When all available candidates have been swiped, a "No more profiles" message
  replaces the card so the user is never left staring at an empty page.

#rule("Permit Easy Reversal of Actions")
The Undo bar remains visible for several seconds after a rejection. Clicking it POSTs to `/discover/undo`,
which deletes the swipe record and reloads the same profile so the user can
reconsider. Only the most recent swipe can be undone, which keeps the undo
semantics simple and predictable.

#rule("Support Internal Locus of Control")
Yellow nudge banners appear when the user's profile is missing key fields or
their schedule is empty. These are informational only,
they link to the Profile and Schedule pages but do not block swiping or force
any action. The user decides when and whether to act on them.

#rule("Offer Simple Error Handling")
The report flow is hidden behind a secondary affordance: clicking "Report"
expands a form with an optional reason field (max 300 characters) and a
confirmation submit. This two-step design prevents accidental reports. The
server also filters out the current user's own profile,
ensuring users can never accidentally see or swipe themselves.

=== User Interactions

- *Accept* a profile: click the green Accept button or press the right arrow
  key. A swipe record is created; if the other user has also accepted, a match
  is formed and a toast confirms it.
- *Reject* a profile: click the red Reject button or press the left arrow key.
  An Undo bar appears at the bottom of the screen.
- *Undo* a rejection: click the Undo bar to delete the swipe and revisit the
  same profile.
- *View compatibility breakdown*: hover the score badge to see a tooltip
  listing what contributed to the score.
- *Act on nudges*: click links in yellow banners to navigate to Profile or
  Schedule.
- *Report* a user: click "Report", optionally enter a reason, and submit.

// ─────────────────────────────────────────────────────────────────────────────
== Chats Page (`/chats`)
// ─────────────────────────────────────────────────────────────────────────────

=== Purpose

The Chats page is the messaging hub. A left sidebar lists all current matches
with their photos and names; the right pane shows the active conversation. Each
conversation opens with an AI-generated icebreaker personalised to the two
users' shared classes and profile traits, streamed in real time from the Google
Gemini API.

=== Screenshot

#screenshot("screenshots/06-chats.png", "Chats: match list on the left, active conversation with icebreaker on the right.")

=== Golden Rules

#rule("Strive for Consistency")
Sent messages are always right-aligned with a brand-blue background; received
messages are left-aligned on a white background. This directional colour
convention is consistent across every conversation and mirrors the established
convention of consumer messaging applications, minimising the learning curve.
Timestamps are shown beneath each message, displayed in the
same position and style throughout.

#rule("Enable Frequent Users to Use Shortcuts")
Pressing *Enter* in the message input sends the message,
matching the universal shortcut expected in every modern chat interface. Users
who exchange many messages per session never need to reach for the Send button.

#rule("Offer Informative Feedback")
- While the Gemini API streams the icebreaker text, a shimmer (skeleton-loader)
  animation fills the icebreaker card so the user knows content is loading
  rather than assuming the feature is broken. Once the icebreaker arrives via
  SSE it is injected into the card along with the *↻ new* regenerate button,
  which only appears after content is present. If the SSE stream fails, an
  explicit error message replaces the shimmer; the user is never left staring
  at an infinite animation.
- When the user sends a message the bubble appears in the conversation
  immediately (optimistic append) before the server confirms, so there is no
  perceptible delay or page reload. Incoming messages from the other person
  are pushed via a dedicated Server-Sent Events stream and appended in real
  time; the user never has to reload to see a reply.
- Incoming messages are marked as read automatically the moment they are
  delivered via SSE, keeping the notification badge accurate without any
  manual action.
- The conversation pane auto-scrolls to the newest message on open and on each
  new send or receive, keeping the latest content in view without manual
  scrolling.
- The match-count label in the sidebar header tells users at a glance how many
  active matches they have.

#rule("Design Dialogue to Yield Closure")
Unmatching requires a two-step confirmation dialog ("Are you sure you want to
unmatch [Name]?"). This deliberate friction prevents accidental deletion of a
conversation and gives the user a clear, intentional exit point.

#rule("Permit Easy Reversal of Actions")
If the first AI-generated icebreaker is unsuitable, the user can click the
*↻ new* button to request a fresh one from the Gemini API.
The regeneration is non-destructive: previous messages in the conversation
are unaffected.

#rule("Support Internal Locus of Control")
Every action in the Chats page is user-initiated: opening a conversation,
sending a message, regenerating an icebreaker, and unmatching. The interface
does not push content or navigate automatically after any of these actions.

#rule("Reduce Short-Term Memory Load")
Each entry in the match sidebar displays the user's profile photo and
display name rather than just a username, so users do not need to map
cryptic usernames to remembered faces.

=== User Interactions

- Click a *match name or photo* in the sidebar to open that conversation.
- Read the *icebreaker card* at the top of the conversation; if it is still
  loading, a shimmer animation indicates progress. Once loaded, the
  *↻ new* button appears on the card.
- Click *↻ new* to discard the current icebreaker and generate a fresh one.
- Type a message and press *Enter* or click the paper-plane *Send* button;
  the bubble appears instantly in the conversation without a page reload.
- Messages from the other person appear in real time via SSE push; no refresh
  is needed to receive them.
- Click a match's *name* in the conversation header to navigate to their full
  profile view.
- Click *Unmatch* and confirm the dialog to end the match and remove the
  conversation.

// ─────────────────────────────────────────────────────────────────────────────
== My Schedule Page (`/schedule`)
// ─────────────────────────────────────────────────────────────────────────────

=== Purpose

The Schedule page lets users build a personal course schedule by entering
Kent State CRNs. The stored schedule serves two functions: it increases the
compatibility score with classmates in the Discover feed (shared CRNs are
worth the most points in the algorithm), and it supplies course context to the
Gemini API when generating icebreakers.

=== Screenshot

#screenshot("screenshots/08-schedule.png", "My Schedule: CRN lookup input, preview table, and saved schedule table.")

=== Golden Rules

#rule("Design Dialogue to Yield Closure")
Adding courses follows a deliberate two-step flow. First the user enters CRNs
and clicks *Look Up*, the server scrapes Kent State's Banner system and
returns a preview table showing CRN, course code, title, days, time, location,
and instructor. Only after reviewing this preview does the user click *Add to
My Schedule* to commit the data. This review step is the closure point: the
user confirms what will be saved before it is saved.

#rule("Offer Informative Feedback")
- The preview table gives full course details before any changes are committed,
  so the user can verify they entered the correct CRNs.
- CRNs that could not be resolved in the Banner system are listed explicitly
  below the table ("The following CRNs were not found: …"), distinguishing
  scraping failures from valid additions.
- After removing a course, a toast notification confirms the deletion and
  presents an Undo button.

#rule("Permit Easy Reversal of Actions")
Each saved course row includes a delete (×) button. After deletion the Undo
toast remains visible long enough for the user to restore the course if they
acted by mistake.

#rule("Offer Simple Error Handling")
If a batch of CRNs is looked up and some are invalid, only the failed CRNs are
flagged, valid ones still appear in the preview and can be added normally.
The user corrects only what failed, not the entire input.

#rule("Reduce Short-Term Memory Load")
By entering only a CRN, the user retrieves all associated course data
automatically. There is no need to manually type course names, building codes,
instructor names, or meeting times, eliminating transcription errors and the
cognitive burden of cross-referencing a separate schedule document.

=== User Interactions

- Enter one or more *CRNs* (comma- or space-separated) and click *Look Up*.
- Review the *preview table*; check which CRNs could not be found.
- Click *Add to My Schedule* to save the previewed courses to the database.
- Click the *× button* on a saved row to remove a course.
- Click *Undo* in the toast to restore the most recently removed course.

// ─────────────────────────────────────────────────────────────────────────────
== Settings Page (`/settings`)
// ─────────────────────────────────────────────────────────────────────────────

=== Purpose

The Settings page is divided into two cards: *Match With?* controls who
appears in the Discover feed (gender, age range, major overlap), and *Account
Information* provides access to password reset and account deletion. Together
they give users full control over their matching preferences and account
lifecycle.

=== Screenshot

#screenshot("screenshots/09-settings.png", "Settings: Match With? preferences on the left, Account Information on the right.")

=== Golden Rules

#rule("Strive for Consistency")
The two-column card layout and button styling match the Profile page. All
destructive actions (Delete Account) use a red button,
consistent with every other irreversible action in the application.

#rule("Offer Informative Feedback")
After saving preferences, a success message ("Settings saved!") appears at the
top of the Match With? card. Client-side validation fires
immediately if all gender checkboxes are deselected and the user tries to save,
an inline error message appears before any network request is made, so the
round-trip is skipped entirely.

#rule("Offer Simple Error Handling")
The only hard validation rule is that at least one gender must be checked. The
error message names the exact problem; the age range and major preference
inputs are unaffected and retain their values. No data is lost when validation
fails.

#rule("Permit Easy Reversal of Actions")
- Clicking *Reset Password* navigates to a dedicated page where no change
  happens until the user completes and submits the new-password form. Navigating
  back from that page leaves the existing password intact.
- The *Delete Account* button triggers a confirmation dialog requiring explicit
  acknowledgement before any irreversible data deletion occurs.

#rule("Support Internal Locus of Control")
Default values cover all genders, all majors, and the full age range (18–99),
so a user who does not want to customise anything can ignore this page
entirely. Every preference is an intentional opt-in or opt-out.

=== User Interactions

- Toggle *Match all majors* to restrict or open major overlap.
- Check or uncheck gender checkboxes (*Men, Women, Nonbinary, Other*).
- Adjust *Min Age* and *Max Age* number inputs (18–99).
- Click *Save Preferences*; a success banner confirms persistence.
- Click *Reset Password* to begin the password-change flow.
- Click *Delete Account* and confirm the dialog to permanently remove all
  account data.

// ─────────────────────────────────────────────────────────────────────────────
== Reset Password Page (`/reset-password`)
// ─────────────────────────────────────────────────────────────────────────────

=== Purpose

The Reset Password page allows an authenticated user to change their account
password. It mirrors the sign-up page's password-confirmation pattern to keep
the mental model consistent for users who have already learned that flow.

=== Screenshot

#screenshot("screenshots/10-reset-password.png", "Reset Password: new password and confirm-password fields, with Cancel link.")

=== Golden Rules

#rule("Strive for Consistency")
The form layout, card style, and validation feedback (inline errors, field
border colour changes) are identical to those used at sign-up. A returning user
who has forgotten the password rules does not need to look them up, the same
conventions apply.

#rule("Offer Informative Feedback")
Server-side validation errors (passwords do not match, too short) are shown as
inline messages without a page reload. On success, a confirmation message
appears briefly before the user is redirected back to Settings.

#rule("Permit Easy Reversal of Actions")
A *Cancel* link returns the user to Settings without making any change. The
existing password remains active until the user explicitly submits a valid new
one.

#rule("Offer Simple Error Handling")
Validation rules (minimum 6 characters, fields must match) are the same as at
sign-up, so users who have been through account creation already know them.
Error messages are specific rather than generic ("Passwords must match" is
distinct from "Password must be at least 6 characters").

=== User Interactions

- Enter *New Password* and *Confirm Password*.
- Click *Update Password* to submit.
- On success: confirmation message, then automatic redirect to Settings.
- On failure: inline error message; correct the relevant field and resubmit.
- Click *Cancel* to return to Settings without any change.

// ─────────────────────────────────────────────────────────────────────────────
== Notifications Page (`/notifications`)
// ─────────────────────────────────────────────────────────────────────────────

=== Purpose

The Notifications page aggregates all actionable alerts into a single location:
new matches, unread message counts, and prompts to complete an incomplete
profile or add a schedule. A numeric badge in the navigation sidebar reflects
the count at all times, so users know whether to visit this page before they
open it.

=== Screenshot

#screenshot("screenshots/11-notifications.png", "Notifications: cards for new matches, unread messages, and profile nudges.")

=== Golden Rules

#rule("Offer Informative Feedback")
Every notification card uses a distinct icon and plain-language description:
"You matched with Jordan", "Riley sent you 3 unread messages", "Complete your
profile with name, age, and photo". The user understands what happened and what
to do next without opening any other page. The sidebar badge provides persistent feedback across the entire application.

#rule("Design Dialogue to Yield Closure")
Each notification type has one primary action button that resolves the
notification: "Chat" opens the relevant conversation, "Open Chat" navigates
directly to unread messages, "Update Profile" links to the profile editor, and
"Add Schedule" links to the schedule page. Clicking the action button is the
natural endpoint of the notification's lifecycle.

#rule("Permit Easy Reversal of Actions")
Match notification cards have a *Dismiss* button that sends a POST to
`/notifications/dismiss` and removes the card. If a user accidentally dismisses
a notification, they can still navigate to Chats to find the match, dismissal
only removes the card, not the match itself.

#rule("Reduce Short-Term Memory Load")
Instead of requiring users to remember they received a match and then navigate
to Chats, the notification system surfaces this context proactively. The badge
counter makes it possible to assess notification status at a glance from any
page.

#rule("Support Internal Locus of Control")
Profile-completeness and schedule nudges are advisory, not blocking. The user
can ignore them indefinitely and continue using Discover and Chats without
completing their profile. The nudges reappear only because the underlying
condition has not changed, not because the system is nagging them.

=== User Interactions

- Browse all active notification cards.
- Click *Chat* on a match notification to open the new match's conversation.
- Click *Dismiss* to remove a match notification (the match is preserved).
- Click *Open Chat* on an unread-message notification to go directly to that
  conversation.
- Click *Update Profile* or *Add Schedule* to navigate to the relevant page.
- The badge count in the sidebar updates to reflect the current number of
  active notifications.

// ─────────────────────────────────────────────────────────────────────────────
== Testimonials Page (`/testimonials`)
// ─────────────────────────────────────────────────────────────────────────────

=== Purpose

The Testimonials page is a community board where users can post short success
stories or endorsements of the platform (up to 300 characters). It provides
social proof for new users and a sense of community for existing ones. Each
user may have at most one active testimonial, which they can edit or delete at
any time.

=== Screenshot

#screenshot("screenshots/12-testimonials.png", "Testimonials: submission textarea with character counter and the community grid.")

=== Golden Rules

#rule("Offer Informative Feedback")
A live character counter ("0 / 300") updates on every keystroke so users
always know how much space remains. The counter turns visually distinct as the
limit approaches, preventing surprise truncation.

#rule("Design Dialogue to Yield Closure")
The submit button's label is context-sensitive: it reads "Share" when the user
has no existing testimonial and "Update" when one already exists. This label
change signals which action will occur before the button is clicked. After
submission, the updated testimonial appears immediately in the grid below,
confirming the save without a separate success message.

#rule("Permit Easy Reversal of Actions")
If a user has submitted a testimonial, a *Delete* button appears alongside
"Update". The user can remove their own testimonial at any time, there is no
waiting period or approval flow.

#rule("Reduce Short-Term Memory Load")
When a user returns to the page after a prior submission, the textarea is
pre-populated with their existing testimonial text. They do not need to
remember what they wrote previously to edit it; they simply modify the
pre-filled content.

=== User Interactions

- Type a testimonial (up to 300 characters); the live counter updates.
- Click *Share* to publish a new testimonial.
- Click *Update* to replace an existing testimonial.
- Click *Delete* to remove an existing testimonial entirely.
- Browse the *testimonial grid* to read other users' posts; posts are displayed
  with the author's profile photo and name.

// ─────────────────────────────────────────────────────────────────────────────
== Profile View Page (`/profile/<id>`)
// ─────────────────────────────────────────────────────────────────────────────

=== Purpose

The Profile View page presents the full profile of another user. It is reached
by clicking a match's name from within the Chats page. It exists because the
Discover card deliberately shows a condensed view; once matched and chatting,
both users benefit from seeing each other's complete information. The page is
access-controlled: only matched users may view each other's profile this way.

=== Screenshot

#screenshot("screenshots/13-profile-view.png", "Profile View: photo, header details, traits pills, and report option.")

=== Golden Rules

#rule("Strive for Consistency")
The layout, profile photo, header row with name, pronouns, age, major, year,
and height, followed by traits displayed as rounded badge pills, exactly
mirrors the card shown in the Discover feed. The user builds a single mental
model for how a person is represented and encounters it consistently across
both contexts.

#rule("Support Internal Locus of Control")
The user arrived here voluntarily by clicking a match's name in Chats. A Back
button at the top of the page returns them to the same conversation without
disrupting scroll position or message state. Navigation is always user-driven.

#rule("Offer Simple Error Handling")
Access is enforced server-side: if an unauthenticated user or a non-matched
user attempts to reach this URL directly, the server rejects the request.
Legitimate matched users always have seamless access; unauthorised access is
blocked without a confusing error page, they are simply redirected.

#rule("Permit Easy Reversal of Actions")
The Report option is hidden behind a secondary interaction: clicking "Report"
expands an inline form with an optional reason text field and a confirmation
submit button. The two-step flow prevents accidental reports
while keeping the option discoverable for users who need it.

=== User Interactions

- Click the *Back arrow* to return to the Chats page.
- View the full profile: photo, name, pronouns, age, year, major, height, and
  traits.
- Click *Report* to expand the report form, optionally enter a reason (max 300
  characters), and submit.

== Navigation Sidebar (Global)

=== Purpose

A slide-out navigation sidebar is available from every authenticated page via
a hamburger button in the top-right corner. It provides access to all seven
major sections of the application, shows the current notification count, and
contains the logout action. Because the same sidebar appears on every page, it
functions as the application's primary navigation layer.

=== Screenshot

#screenshot("screenshots/07-sidebar.png", "Navigation sidebar: links with icons, notification badge on the bell, and the Logout button.")

=== Golden Rules

#rule("Strive for Consistency")
The hamburger button occupies the same top-right position on every page.
The sidebar always lists the same seven links in the same order with the same
icons. After even a short session, users can navigate by muscle memory without
reading labels.

#rule("Enable Frequent Users to Use Shortcuts")
The *Escape key* closes the sidebar immediately. Clicking any navigation link
navigates instantly without a confirmation step. Pressing *?* from any page
opens a floating help overlay that lists every keyboard shortcut in the
application. These behaviours allow frequent users to open and dismiss the
sidebar, navigate the whole app, and recall shortcuts without reaching for
the mouse.

#rule("Offer Informative Feedback")
The notification bell icon carries a live numeric badge showing the count of
unread notifications. This badge is rendered on every authenticated page so the
user always knows their notification status at a glance, without needing to
visit the Notifications page.

#rule("Permit Easy Reversal of Actions")
Three separate mechanisms close the sidebar without navigating: the × button
inside the sidebar, pressing Escape, or clicking the semi-transparent overlay
behind the sidebar. The user can open and close it as many times as needed
with minimal friction.

#rule("Design Dialogue to Yield Closure")
The *Log Out* action requires a confirmation dialog before the session is
ended. This prevents accidental logouts, particularly
important on shared devices, and gives the user a clear, intentional endpoint
to the session lifecycle.

=== User Interactions

- Click the *hamburger icon* (☰) to open the sidebar.
- Click any nav link (Discover, My Profile, Chats, Notifications, Schedule,
  Testimonials, Settings) to navigate.
- Close the sidebar by clicking the *× button*, clicking the *overlay*, or
  pressing *Escape*.
- Click *Log Out* and confirm the dialog to end the session.

// ─────────────────────────────────────────────────────────────────────────────
== Global Keyboard Shortcuts (All Authenticated Pages)
// ─────────────────────────────────────────────────────────────────────────────

=== Purpose

Every page in the application includes a global keyboard shortcut layer. Single
key presses jump to any section without opening the sidebar. Pressing *?*
opens a floating help overlay that lists every binding, grouped into Navigation,
Account, and Utility categories, with styled `kbd` chips for each key. Shortcuts
are suppressed automatically while focus is inside any input, textarea, or
select element so they never interfere with form entry. Escape is the one
exception: it always fires and dismisses whatever is active — a modal, the
shortcuts overlay, or the currently focused element.

=== Screenshot

#screenshot("screenshots/14-keyboard-shortcuts.png", "Keyboard shortcuts overlay: the ? help panel listing all bindings grouped by Navigation, Account, and Utility.")

=== Keyboard Shortcut Reference

#table(
  columns: (auto, 1fr),
  inset: 6pt,
  stroke: 0.4pt + luma(160),
  [*Key*], [*Action*],
  [*Navigation*], [],
  [`h`], [Go to Landing / Home],
  [`d`], [Go to Discover],
  [`c`], [Go to Chats],
  [`n`], [Go to Notifications],
  [`p`], [Go to My Profile],
  [`s`], [Go to My Schedule],
  [`t`], [Go to Testimonials],
  [*Account*], [],
  [`,`], [Go to Settings],
  [`Shift+L`], [Go to Login],
  [`Shift+R`], [Go to Sign Up],
  [*Utility*], [],
  [`Escape`], [Close modal / dismiss overlay / blur focused element],
  [`?`], [Toggle keyboard shortcuts help overlay],
)

=== Golden Rules

#rule("Enable Frequent Users to Use Shortcuts")
The shortcut system exists solely for returning users who have internalised
the application's layout. A first-time visitor can ignore every binding
entirely. An experienced user can navigate across all seven major sections,
reach Settings, and trigger or dismiss the help overlay without any mouse
interaction. The single-letter mnemonics map directly to page names
(d=Discover, c=Chats, n=Notifications, p=Profile, s=Schedule, t=Testimonials),
keeping the set learnable.

#rule("Reduce Short-Term Memory Load")
Because the shortcuts are not labelled on screen, the *?* overlay externalises
the complete list so users never have to memorise all twelve bindings at once.
Grouping the overlay into three sections (Navigation, Account, Utility) reduces
the scanning cost: a user looking for a navigation shortcut does not need to
read the utility bindings.

#rule("Offer Informative Feedback")
Opening the overlay provides immediate visual confirmation that the shortcut
system is active and shows exactly which keys are bound. Closing the overlay
with Escape, the Close button, or the backdrop collapses it instantly, giving
clear feedback that the application returned to its normal state.

=== User Interactions

- Press any navigation key (`h`, `d`, `c`, `n`, `p`, `s`, `t`) while not
  typing in a field to jump directly to the corresponding page.
- Press *,* to go to Settings; *Shift+L* to go to Login; *Shift+R* to go
  to Sign Up.
- Press *?* to open the shortcuts overlay; press *Escape*, click *Close*,
  or click the backdrop to dismiss it.
- All shortcuts except Escape are suppressed when focus is inside an input,
  textarea, or select element.

