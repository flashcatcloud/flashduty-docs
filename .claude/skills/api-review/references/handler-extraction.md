# Handler extraction

How to pull a real OpenAPI input/output schema out of a Go handler in a Flashduty backend repo. This is the trickiest part of the skill, and being disciplined here is what separates a useful spec from hallucinated noise.

## The pattern to look for

Every public Flashduty handler looks roughly like this:

```go
type infoInput struct {
    IncidentID primitive.ObjectID `json:"incident_id" binding:"required"`
}

func Info(c *gin.Context) {
    ctx := srv.GinToCtx(c)

    input := new(infoInput)
    if err := srv.Validate(ctx, input); err != nil {
        srv.JSON(ctx, srv.NewErrorWithMsg(srv.ErrInvalidParameter, err.Error()))
        return
    }

    user := structs.GetUser(ctx)
    doc, err := incident.NewIncidentLogic(ctx).GetIncidentByID(user.AccountID, input.IncidentID)
    if err != nil {
        srv.JSON(ctx, srv.ToError(err, srv.ErrInternalError))
        return
    }

    item := logic.IncidentDocToItem(doc)
    srv.JSON(ctx, item)
}
```

From this we need four things:

1. **Input struct name.** `infoInput` — the type passed to `srv.Validate`. Sometimes it's bound instead via `c.ShouldBindJSON(input)` or `c.ShouldBindQuery(input)`. All three behave identically for our purposes.
2. **Input struct source.** Usually the same file, just above the handler. Follow embedded struct references into sibling files or into `structs/` or `model/` packages.
3. **Output value.** The expression passed to `srv.JSON(ctx, <value>)` on the *success branch*. Ignore error branches — they all hit `srv.JSON(ctx, srv.NewError...)` and are already handled by the shared `ErrorResponse`.
4. **Output type.** The Go type of that success value — `*structs.IncidentItem`, `[]*structs.ChannelItem`, `*logic.ListResult[structs.AlertItem]`, or an anonymous `gin.H` / struct literal.

## Finding the handler file for a given path

Flashduty backends follow loose conventions, not a single rule. Try these in order:

1. **File-name convention in fc-event.** `/<feature>/<op>` → `cmd/server/controller/<feature>/<op>.go`. Replace `-` with `_` in both feature and op segments. This hits ~70% of fc-event cleanly.
2. **`grep` for the quoted path string** in `routes.go` files:
   ```bash
   git -C <repo> grep -l '"/template/info"' origin/main
   ```
   Routes files typically contain `engine.POST("/template/info", template.Info)` — that points you at the package *and* the handler function.
3. **`grep` for a likely handler name** derived from the last URL segment. `/template/preview` → `func Preview(`. Cross-check by confirming the function takes `*gin.Context` and calls `srv.GinToCtx` or `srv.JSON`.
4. **Last resort: grep for the registry's `Name`.** Handlers sometimes reference the permission name (`template:write:create`) in a permission check; that pins the file.

Record the repo-relative path into findings (`handler.file`). Do not embed absolute paths — those don't travel.

## Walking an input struct

When you read a Go struct definition, treat each field like this:

| Go field shape | OpenAPI mapping |
|---|---|
| `Foo string \`json:"foo"\`` | `foo: {type: string}` |
| `Foo string \`json:"foo" binding:"required"\`` | add `foo` to `required` |
| `Foo int64 \`json:"foo,omitempty"\`` | `foo: {type: integer, format: int64}`, not required |
| `Foo *int64 \`json:"foo"\`` | same as above; pointer implies optional |
| `Foo bool \`json:"foo"\`` | `foo: {type: boolean}` |
| `Foo time.Time \`json:"foo"\`` | `foo: {type: string, format: date-time}` |
| `Foo primitive.ObjectID \`json:"foo"\`` | `foo: {type: string, pattern: "^[0-9a-fA-F]{24}$", description: "MongoDB ObjectID."}` |
| `Foo []string \`json:"foo"\`` | `foo: {type: array, items: {type: string}}` |
| `Foo []Bar \`json:"foo"\`` | `foo: {type: array, items: {$ref: Bar}}` |
| `Foo map[string]string \`json:"foo"\`` | `foo: {type: object, additionalProperties: {type: string}}` |
| `Foo Bar \`json:"foo"\`` (named struct) | `foo: {$ref: Bar}`, register Bar in components.schemas |
| `Bar \`json:"bar"\`` (embedded struct with json tag) | nest under `bar` |
| `Bar` (embedded struct, no json tag) | inline Bar's fields into the parent |
| `Foo string \`json:"-"\`` | skip |
| `binding:"required"` | add to parent's `required` array |
| `binding:"oneof=a b c"` | add `enum: ["a","b","c"]` |
| `binding:"max=N,min=M"` (numeric) | `maximum: N, minimum: M` (inclusive) |
| `binding:"max=N,min=M"` (string) | `maxLength: N, minLength: M` (inclusive) |
| `binding:"gte=N,lte=N"` (numeric) | same as `min`/`max` — inclusive |
| `binding:"gt=N,lt=N"` (numeric) | `exclusiveMinimum: N, exclusiveMaximum: N` |
| `binding:"gte=N,lt=N"` (string) | `minLength: N, maxLength: N-1` (OpenAPI has no `exclusiveMaxLength`; convert) |
| `binding:"len=N"` | `minLength: N, maxLength: N` |
| `binding:"e164"` | `format: "phone"` plus `pattern: "^\\\\+[1-9]\\\\d{1,14}$"` |
| `binding:"email"` | `format: "email"` |
| `binding:"url"` | `format: "uri"` |
| `binding:"uuid"` | `format: "uuid"` |
| `gorm:"serializer:json"` | walk the field's Go type as normal — it's just stored as JSON in the DB |

### Critical: be faithful to the binding tags

**Only emit a constraint if it's in the tag.** This is the single easiest place to add made-up rules that drift from reality:

- Don't add an `enum` because the handler `switch`es on specific values — the handler may accept anything and only branch on the recognized set. Enum means "the server rejects everything else," which must be in `binding:"oneof=..."`.
- Don't mark fields `required` because "it wouldn't make sense without them" — only if the tag says so.
- Don't invent `pattern` regexes beyond the structural ones in the table above (ObjectID, email, etc.).

### Default values

Scan the handler body for lines like `if input.X == 0 { input.X = 20 }` or `if len(input.X) == 0 { input.X = "default" }`. These are runtime-applied defaults — emit them as OpenAPI `default`. API consumers rely on knowing "what happens if I don't send this field".

### Output enum values

For *output* schemas, documenting enums based on Go constants is legitimate and useful, even though bindings don't apply. When an output field holds a status/type/kind string, find the `const` block defining the allowed values (usually next to the model definition) and emit them as `enum` with a brief note in the description. Verify the actual string literal values by reading the const block — don't guess them from the constant name.

### Required on response schemas — use `omitempty` as the signal

Input schemas get `required` from `binding:"required"` tags. **Response schemas** get `required` from a different signal: whether the Go field carries `omitempty`.

- Field without `omitempty` → always serialized (even with a zero value) → mark `required` on the response schema.
- Field with `omitempty` → may be absent when zero-valued → not required.

Example — `structs.TemplateItem`:

```go
type TemplateItem struct {
    AccountID     int64              `json:"account_id"`            // always present → required
    TemplateID    primitive.ObjectID `json:"template_id"`           // always present → required
    DeletedAt     int64              `json:"deleted_at,omitempty"`  // conditional → not required
    CreatedAt     int64              `json:"created_at"`            // always present → required
}
```

The response schema for this struct should list every field except `deleted_at` in `required`. Skipping this tells consumers "every field is optional" which is wrong — it forces them to defensively nil-check fields that the server guarantees to populate. Always walk the Go struct and compute the required array from the tag set.

Embedded structs with a `json:"foo"` tag are tricky: they produce nested objects, not inlined fields. Always check for that tag.

## Walking an output value

The Go value passed to `srv.JSON(ctx, X)` can be a few shapes:

1. **A pointer/value of a named struct.** Easy case. Register the struct under `components.schemas.<TypeName>`, reference via `$ref`.
2. **A slice.** Emit `{type: array, items: {$ref: <TypeName>}}`.
3. **A `gin.H` or inline struct literal** like `gin.H{"items": items, "total": total}`. These are common for list endpoints. Walk each key manually: look up the Go type of each value expression and emit a property per key. Name the resulting schema `<OperationName>Response` or similar.
4. **A generic wrapper.** Flashduty uses a few list wrappers — `pgy.ListResult[T]`, `logic.Paginated[T]`, etc. Treat them as `{items: [T], total: integer}` even if the wrapper has extra metadata fields; check the wrapper's definition to confirm.
5. **A `map[string]X`.** Emit `{type: object, additionalProperties: X}`.

If you can't resolve the value confidently, don't invent one. Emit:

```json
"data": {
  "type": "object",
  "description": "Shape not resolvable from current Go sources; see handler <file>."
}
```

and add an entry to findings' `unresolved` list.

## Descriptions

Extract them from, in priority order:

1. The registry row's `Description` field (if non-empty) — this is a human-authored sentence the team has added for ops/audit.
2. The Go doc comment above the handler function (`// Info returns the incident detail including attached alerts.`). Strip the leading comment marker.
3. The registry's `NameCN` translated via the glossary (fall-back for Chinese files; for English files, translate via glossary).

Field-level descriptions come from Go doc comments above the struct field when available. If none exist, leave `description` empty — it's better than inventing text.

## What to avoid

- **Don't invent field names** that aren't in the Go source. If a struct has 3 fields, the schema has 3 properties. Do not pad based on "this feels like an API that should have X".
- **Don't duplicate schemas.** If two handlers return the same `*structs.ChannelItem`, both operations reference the same `$ref: '#/components/schemas/ChannelItem'`.
- **Don't flatten for convenience.** If an output has a nested struct, keep the nesting. `incident: { id, name, status }` stays `incident: {...}`, it does not become `incident_id`, `incident_name`, `incident_status`.
- **Don't guess at required-ness.** Only mark a field `required` if it has `binding:"required"` in its tag. Everything else is optional.
- **Don't emit `nullable`.** OpenAPI 3.1 uses type unions (`type: [string, "null"]`) but these are noisy; simply keeping a field off the `required` list is sufficient for our purposes.
