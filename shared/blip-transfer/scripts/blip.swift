#!/usr/bin/env swift

import Foundation
import AppKit
import ApplicationServices
import CoreGraphics
import Darwin

private let blipBundleIdentifier = "net.blip.macos"
private let blipServiceName = "Blip…"
private let maximumAXDepth = 14
private let maximumAXElements = 1_500

private struct CommandError: Error {
    let code: String
    let message: String
    let details: [String: Any]

    init(_ code: String, _ message: String, details: [String: Any] = [:]) {
        self.code = code
        self.message = message
        self.details = details
    }
}

private func jsonSafe(_ value: Any) -> Any {
    switch value {
    case let dictionary as [String: Any]:
        return dictionary.mapValues(jsonSafe)
    case let array as [Any]:
        return array.map(jsonSafe)
    case let string as String:
        return string
    case let number as NSNumber:
        return number
    case is NSNull:
        return NSNull()
    default:
        return String(describing: value)
    }
}
private func jsonValue(_ value: Any?) -> Any {
    value ?? NSNull()
}

private func emit(_ object: [String: Any]) {
    let safe = jsonSafe(object)
    guard JSONSerialization.isValidJSONObject(safe),
          let data = try? JSONSerialization.data(withJSONObject: safe, options: [.sortedKeys]),
          let text = String(data: data, encoding: .utf8) else {
        fputs("{\"ok\":false,\"error\":{\"code\":\"json_encoding_failed\",\"message\":\"Could not encode result\"}}\n", stderr)
        return
    }
    print(text)
}

private func fail(_ error: CommandError) -> Never {
    var payload: [String: Any] = [
        "ok": false,
        "error": [
            "code": error.code,
            "message": error.message,
            "details": error.details
        ]
    ]
    if error.details.isEmpty {
        payload["error"] = ["code": error.code, "message": error.message]
    }
    emit(payload)
    exit(1)
}

private func redactEmails(_ input: String) -> String {
    let pattern = #"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"#
    guard let expression = try? NSRegularExpression(pattern: pattern) else { return input }
    let range = NSRange(input.startIndex..<input.endIndex, in: input)
    return expression.stringByReplacingMatches(in: input, range: range, withTemplate: "[redacted-email]")
}

private func cleaned(_ value: String?) -> String? {
    guard let value else { return nil }
    let result = value.trimmingCharacters(in: .whitespacesAndNewlines)
    return result.isEmpty ? nil : result
}
private func containsEmailAddress(_ input: String) -> Bool {
    redactEmails(input) != input
}

private func axAttribute(_ element: AXUIElement, _ name: String) -> CFTypeRef? {
    var value: CFTypeRef?
    guard AXUIElementCopyAttributeValue(element, name as CFString, &value) == .success else {
        return nil
    }
    return value
}

private func axString(_ element: AXUIElement, _ name: String) -> String? {
    guard let value = axAttribute(element, name) else { return nil }
    if let string = value as? String { return cleaned(string) }
    if let attributed = value as? NSAttributedString { return cleaned(attributed.string) }
    return nil
}

private func axRole(_ element: AXUIElement) -> String {
    axString(element, kAXRoleAttribute as String) ?? ""
}

private func axChildren(_ element: AXUIElement) -> [AXUIElement] {
    guard let value = axAttribute(element, kAXChildrenAttribute as String) else { return [] }
    return value as? [AXUIElement] ?? []
}

private func axElementAttribute(_ element: AXUIElement, _ name: String) -> AXUIElement? {
    guard let value = axAttribute(element, name), CFGetTypeID(value) == AXUIElementGetTypeID() else {
        return nil
    }
    return (value as! AXUIElement)
}

private func sameElement(_ lhs: AXUIElement, _ rhs: AXUIElement) -> Bool {
    CFEqual(lhs, rhs)
}

private func axFrame(_ element: AXUIElement) -> CGRect? {
    guard let positionValue = axAttribute(element, kAXPositionAttribute as String),
          let sizeValue = axAttribute(element, kAXSizeAttribute as String),
          CFGetTypeID(positionValue) == AXValueGetTypeID(),
          CFGetTypeID(sizeValue) == AXValueGetTypeID() else {
        return nil
    }

    var origin = CGPoint.zero
    var size = CGSize.zero
    guard AXValueGetValue((positionValue as! AXValue), .cgPoint, &origin),
          AXValueGetValue((sizeValue as! AXValue), .cgSize, &size),
          origin.x.isFinite, origin.y.isFinite, size.width.isFinite, size.height.isFinite,
          size.width > 1, size.height > 1 else {
        return nil
    }
    return CGRect(origin: origin, size: size)
}

private func rawLabels(_ element: AXUIElement) -> [String] {
    let names = [
        kAXTitleAttribute as String,
        kAXValueAttribute as String,
        kAXDescriptionAttribute as String,
        kAXHelpAttribute as String,
        "AXIdentifier"
    ]
    var seen = Set<String>()
    var labels: [String] = []
    for name in names {
        if let value = axString(element, name), seen.insert(value).inserted {
            labels.append(value)
        }
    }
    return labels
}

private struct AXNode {
    let element: AXUIElement
    let parent: Int?
    let depth: Int
    let role: String
    let subrole: String?
    let labels: [String]
    let frame: CGRect?
}

private struct AXTree {
    let nodes: [AXNode]
    let truncated: Bool
}

private func buildAXTree(from roots: [AXUIElement], maxDepth: Int = maximumAXDepth, maxCount: Int = maximumAXElements) -> AXTree {
    var nodes: [AXNode] = []
    var truncated = false

    func contains(_ element: AXUIElement) -> Bool {
        nodes.contains { sameElement($0.element, element) }
    }

    func visit(_ element: AXUIElement, parent: Int?, depth: Int) {
        guard nodes.count < maxCount else {
            truncated = true
            return
        }
        guard !contains(element) else { return }

        let index = nodes.count
        nodes.append(AXNode(
            element: element,
            parent: parent,
            depth: depth,
            role: axRole(element),
            subrole: axString(element, kAXSubroleAttribute as String),
            labels: rawLabels(element),
            frame: axFrame(element)
        ))

        let children = axChildren(element)
        guard depth < maxDepth else {
            if !children.isEmpty { truncated = true }
            return
        }
        for child in children {
            visit(child, parent: index, depth: depth + 1)
            if nodes.count >= maxCount {
                truncated = true
                return
            }
        }
    }

    for root in roots {
        visit(root, parent: nil, depth: 0)
        if nodes.count >= maxCount {
            truncated = true
            break
        }
    }
    return AXTree(nodes: nodes, truncated: truncated)
}

private func labelForStaticText(_ node: AXNode) -> String? {
    guard node.role == (kAXStaticTextRole as String) else { return nil }
    return node.labels.first.flatMap(cleaned)
}

private func runningBlipApplications() -> [NSRunningApplication] {
    NSRunningApplication.runningApplications(withBundleIdentifier: blipBundleIdentifier)
}

private func blipApplicationURL() -> URL? {
    NSWorkspace.shared.urlForApplication(withBundleIdentifier: blipBundleIdentifier)
}

private func screenIsLocked() -> Bool {
    let session = CGSessionCopyCurrentDictionary() as? [String: Any] ?? [:]
    return (session["CGSSessionScreenIsLocked"] as? NSNumber)?.boolValue == true
}

private func requireTrustedAccessibility() throws {
    guard AXIsProcessTrusted() else {
        throw CommandError(
            "accessibility_not_trusted",
            "The current host process is not trusted for Accessibility. Run request-permission and grant access in System Settings."
        )
    }
    guard !screenIsLocked() else {
        throw CommandError("screen_locked", "The macOS session is locked. Ask the user to unlock it before inspecting or operating Blip; do not change Accessibility permissions.")
    }
}

private func requireSingleRunningBlip() throws -> (NSRunningApplication, AXUIElement) {
    guard blipApplicationURL() != nil else {
        throw CommandError("blip_not_installed", "Could not locate the Blip application by bundle identifier \(blipBundleIdentifier).")
    }
    let applications = runningBlipApplications()
    guard applications.count == 1, let application = applications.first else {
        throw CommandError(
            applications.isEmpty ? "blip_not_running" : "ambiguous_blip_process",
            applications.isEmpty ? "Blip is not running." : "More than one running Blip process matched the bundle identifier.",
            details: ["matchingProcessCount": applications.count]
        )
    }
    return (application, AXUIElementCreateApplication(application.processIdentifier))
}

private func axWindows(_ application: AXUIElement) -> [AXUIElement] {
    guard let value = axAttribute(application, kAXWindowsAttribute as String) else { return [] }
    return value as? [AXUIElement] ?? []
}

private func windowTitle(_ window: AXUIElement) -> String {
    axString(window, kAXTitleAttribute as String) ?? ""
}

private func commandDoctor() {
    let applicationURL = blipApplicationURL()
    let bundle = applicationURL.flatMap(Bundle.init(url:))
    let running = runningBlipApplications()
    emit([
        "ok": true,
        "command": "doctor",
        "bundleIdentifier": blipBundleIdentifier,
        "installed": applicationURL != nil,
        "applicationPath": jsonValue(applicationURL?.path),
        "version": jsonValue(bundle?.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String),
        "build": jsonValue(bundle?.object(forInfoDictionaryKey: "CFBundleVersion") as? String),
        "running": !running.isEmpty,
        "matchingProcessCount": running.count,
        "accessibilityTrusted": AXIsProcessTrusted(),
        "screenLocked": screenIsLocked()
    ])
}

private func commandRequestPermission() throws {
    let promptKey = kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String
    let trustedAfterRequest = AXIsProcessTrustedWithOptions([promptKey: true] as CFDictionary)
    guard let settingsURL = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") else {
        throw CommandError("settings_url_invalid", "Could not construct the Accessibility settings URL.")
    }
    let openedSettings = NSWorkspace.shared.open(settingsURL)
    emit([
        "ok": true,
        "command": "request-permission",
        "authorizationPromptRequested": true,
        "accessibilityTrusted": trustedAfterRequest,
        "settingsOpened": openedSettings,
        "note": "Only the user can grant Accessibility permission. Re-run doctor after granting it."
    ])
}

private func windowStatus(_ window: AXUIElement) throws -> [String: Any] {
    let tree = buildAXTree(from: [window])
    guard !tree.truncated else {
        throw CommandError(
            "ax_enumeration_limit",
            "A Blip window exceeded the bounded Accessibility inspection limit.",
            details: ["window": redactEmails(windowTitle(window)), "maximumDepth": maximumAXDepth, "maximumElements": maximumAXElements]
        )
    }
    var texts: [String] = []
    var seen = Set<String>()
    for node in tree.nodes {
        guard let raw = labelForStaticText(node) else { continue }
        let redacted = redactEmails(raw)
        if seen.insert(redacted).inserted { texts.append(redacted) }
    }
    return [
        "title": redactEmails(windowTitle(window)),
        "staticText": texts
    ]
}

private func commandStatus() throws {
    try requireTrustedAccessibility()
    let (_, application) = try requireSingleRunningBlip()
    let windows = axWindows(application)
    var result: [[String: Any]] = []
    for window in windows {
        result.append(try windowStatus(window))
    }
    emit([
        "ok": true,
        "command": "status",
        "windows": result,
        "note": "Raw Accessibility text only; no delivery or completion state is inferred."
    ])
}

private let nonRecipientLabels: Set<String> = [
    "blip", "devices", "nearby", "recent", "send", "cancel", "done", "close", "open blip",
    "settings", "settings…", "preferences", "preferences…", "quit blip", "to:", "search",
    "online", "offline", "available", "unavailable", "waiting", "connecting", "connected",
    "no devices", "no devices found", "no one nearby"
]

private func isPlausibleRecipientLabel(_ label: String) -> Bool {
    let normalized = label.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !normalized.isEmpty, normalized.count <= 256 else { return false }
    let lower = normalized.lowercased()
    guard !nonRecipientLabels.contains(lower), !lower.hasSuffix(":"), !lower.hasPrefix("waiting for ") else { return false }
    return true
}

private let rowRoles: Set<String> = [
    kAXRowRole as String,
    kAXCellRole as String,
    kAXButtonRole as String,
    kAXRadioButtonRole as String,
    kAXMenuItemRole as String,
    kAXGroupRole as String
]

private let listRoles: Set<String> = [
    kAXListRole as String,
    kAXTableRole as String,
    kAXOutlineRole as String,
    kAXScrollAreaRole as String
]

private struct RecipientRow {
    let name: String
    let element: AXUIElement
    let role: String
    let frame: CGRect
}

private func nearestRowIndex(for nodeIndex: Int, in tree: AXTree) -> Int? {
    var current = tree.nodes[nodeIndex].parent
    while let index = current {
        let node = tree.nodes[index]
        if rowRoles.contains(node.role), node.frame != nil { return index }
        if node.role == (kAXWindowRole as String) { return nil }
        current = node.parent
    }
    return nil
}

private func hasListContext(_ rowIndex: Int, in tree: AXTree) -> Bool {
    let row = tree.nodes[rowIndex]
    if row.role == (kAXRowRole as String) || row.role == (kAXCellRole as String) || row.role == (kAXMenuItemRole as String) {
        return true
    }
    var current = row.parent
    while let index = current {
        let node = tree.nodes[index]
        if listRoles.contains(node.role) { return true }
        if node.role == (kAXWindowRole as String) { break }
        current = node.parent
    }
    return false
}

private func recipientRows(in tree: AXTree) -> [RecipientRow] {
    var rows: [RecipientRow] = []
    for (index, node) in tree.nodes.enumerated() {
        guard let label = labelForStaticText(node), !containsEmailAddress(label), isPlausibleRecipientLabel(label),
              let rowIndex = nearestRowIndex(for: index, in: tree),
              hasListContext(rowIndex, in: tree),
              let frame = tree.nodes[rowIndex].frame else {
            continue
        }
        let rowNode = tree.nodes[rowIndex]
        if rows.contains(where: { $0.name == label && sameElement($0.element, rowNode.element) }) { continue }
        rows.append(RecipientRow(name: label, element: rowNode.element, role: rowNode.role, frame: frame))
    }
    return rows
}

private func menuBars(for application: AXUIElement) -> [AXUIElement] {
    var bars: [AXUIElement] = []
    func appendUnique(_ element: AXUIElement?) {
        guard let element, !bars.contains(where: { sameElement($0, element) }) else { return }
        bars.append(element)
    }
    appendUnique(axElementAttribute(application, "AXExtrasMenuBar"))
    appendUnique(axElementAttribute(application, kAXMenuBarAttribute as String))
    for child in axChildren(application) where axRole(child) == (kAXMenuBarRole as String) {
        appendUnique(child)
    }
    return bars
}

private func findBlipStatusItem(in application: AXUIElement) throws -> AXUIElement {
    let bars = menuBars(for: application)
    let extrasMenuBar = axElementAttribute(application, "AXExtrasMenuBar")
    let mainMenuBar = axElementAttribute(application, kAXMenuBarAttribute as String)
    var candidates: [AXUIElement] = []
    for bar in bars {
        let isExtras = extrasMenuBar.map { sameElement(bar, $0) } == true
        let isMain = mainMenuBar.map { sameElement(bar, $0) } == true
        // Inspect direct bar items only: an open popover or application's main
        // menus can be deep, but neither is part of status-item identification.
        for item in axChildren(bar) {
            let role = axRole(item)
            guard role == (kAXMenuBarItemRole as String) || role == "AXStatusItem" else { continue }
            let labels = rawLabels(item).map { $0.lowercased() }
            let isStatus = labels.contains("status menu") || role == "AXStatusItem"
            guard isExtras || (!isMain && isStatus) else { continue }
            if !candidates.contains(where: { sameElement($0, item) }) { candidates.append(item) }
        }
    }
    guard candidates.count == 1, let item = candidates.first else {
        throw CommandError("status_menu_unresolved", "Could not uniquely identify Blip's native status item.", details: ["matchingItemCount": candidates.count])
    }
    return item
}

private func uniqueElements(_ elements: [AXUIElement]) -> [AXUIElement] {
    var result: [AXUIElement] = []
    for element in elements where !result.contains(where: { sameElement($0, element) }) {
        result.append(element)
    }
    return result
}

private func deviceRows(from scopes: [AXUIElement]) throws -> [RecipientRow] {
    let tree = buildAXTree(from: uniqueElements(scopes))
    guard !tree.truncated else {
        throw CommandError(
            "ax_enumeration_limit",
            "Blip's device UI exceeded the bounded Accessibility inspection limit.",
            details: ["maximumDepth": maximumAXDepth, "maximumElements": maximumAXElements]
        )
    }
    return recipientRows(in: tree)
}

private func commandDevices() throws {
    try requireTrustedAccessibility()
    let (_, application) = try requireSingleRunningBlip()
    let statusItem = try findBlipStatusItem(in: application)

    let existingPopoverWindows = axWindows(application).filter {
        (axString($0, kAXSubroleAttribute as String) ?? "").localizedCaseInsensitiveContains("popover")
    }
    var scopes = [statusItem] + existingPopoverWindows
    var rows = try deviceRows(from: scopes)
    var openedStatusItem = false

    if rows.isEmpty {
        var actions: CFArray?
        let actionResult = AXUIElementCopyActionNames(statusItem, &actions)
        let availableActions = (actions as? [String]) ?? []
        guard actionResult == .success, availableActions.contains(kAXPressAction as String) else {
            throw CommandError("status_item_not_pressable", "The uniquely identified Blip status item does not expose AXPress.")
        }

        let before = axWindows(application)
        guard AXUIElementPerformAction(statusItem, kAXPressAction as CFString) == .success else {
            throw CommandError("status_item_open_failed", "Could not open the Blip status item through Accessibility.")
        }
        openedStatusItem = true
        usleep(300_000)

        let after = axWindows(application)
        let added = after.filter { candidate in !before.contains(where: { sameElement($0, candidate) }) }
        let popovers = after.filter {
            let subrole = axString($0, kAXSubroleAttribute as String) ?? ""
            return subrole.localizedCaseInsensitiveContains("popover") || subrole.localizedCaseInsensitiveContains("dialog")
        }
        scopes = [statusItem] + added + popovers
        rows = try deviceRows(from: scopes)
    }

    guard !rows.isEmpty else {
        throw CommandError(
            "no_inspectable_recipient_rows",
            "The Blip status UI exposed no inspectable live recipient rows; no device names were guessed.",
            details: ["statusItemOpened": openedStatusItem]
        )
    }

    let outputRows = rows.map { row in
        [
            "display_name": redactEmails(row.name),
            "role": row.role
        ]
    }
    emit([
        "ok": true,
        "command": "devices",
        "statusItemOpened": openedStatusItem,
        "devices": outputRows,
        "note": "Names come from the current Accessibility hierarchy. Email-looking text is redacted; no recipient was selected."
    ])
}

private func validateTransferPaths(_ arguments: [String]) throws -> [String] {
    guard !arguments.isEmpty else {
        throw CommandError("empty_transfer", "prepare requires at least one absolute file or folder path.")
    }
    var paths: [String] = []
    var seen = Set<String>()
    for argument in arguments {
        guard (argument as NSString).isAbsolutePath else {
            throw CommandError("path_not_absolute", "Every transfer path must be absolute.", details: ["path": argument])
        }
        let path = URL(fileURLWithPath: argument).standardizedFileURL.path
        var isDirectory: ObjCBool = false
        guard FileManager.default.fileExists(atPath: path, isDirectory: &isDirectory) else {
            throw CommandError("path_not_found", "A transfer path does not exist.", details: ["path": path])
        }
        guard FileManager.default.isReadableFile(atPath: path) else {
            throw CommandError("path_not_readable", "A transfer path is not readable.", details: ["path": path])
        }
        if seen.insert(path).inserted { paths.append(path) }
    }
    return paths
}

private func commandPrepare(paths arguments: [String]) throws {
    guard blipApplicationURL() != nil else {
        throw CommandError("blip_not_installed", "Could not locate the Blip application by bundle identifier \(blipBundleIdentifier).")
    }
    let paths = try validateTransferPaths(arguments)
    try requireTrustedAccessibility()
    let pasteboard = NSPasteboard.withUniqueName()
    pasteboard.clearContents()
    let URLs = paths.map { NSURL(fileURLWithPath: $0) }
    guard pasteboard.writeObjects(URLs) else {
        pasteboard.releaseGlobally()
        throw CommandError("pasteboard_url_write_failed", "Could not write file URLs to the private named pasteboard.")
    }
    let filenamesType = NSPasteboard.PasteboardType("NSFilenamesPboardType")
    guard pasteboard.setPropertyList(paths, forType: filenamesType) else {
        pasteboard.releaseGlobally()
        throw CommandError("pasteboard_filenames_write_failed", "Could not write the legacy filename representation to the private named pasteboard.")
    }
    guard NSPerformService(blipServiceName, pasteboard) else {
        pasteboard.releaseGlobally()
        throw CommandError("blip_service_failed", "macOS did not invoke the Blip service.")
    }
    emit([
        "ok": true,
        "command": "prepare",
        "state": "chooser-requested",
        "pasteboard": pasteboard.name.rawValue,
        "paths": paths,
        "service": blipServiceName,
        "note": "Preparation requested a chooser; it did not select a recipient and does not prove transmission. Retain this pasteboard until Blip has ingested it, then release it explicitly."
    ])
}

private func commandReleasePasteboard(_ name: String) throws {
    guard name.hasPrefix("CFPasteboardUnique-") else {
        throw CommandError("pasteboard_name_rejected", "Only private pasteboards whose names begin with CFPasteboardUnique- may be released.")
    }
    guard name.count > "CFPasteboardUnique-".count else {
        throw CommandError("pasteboard_name_rejected", "The private pasteboard name is incomplete.")
    }
    NSPasteboard(name: NSPasteboard.Name(name)).releaseGlobally()
    emit([
        "ok": true,
        "command": "release-pasteboard",
        "pasteboard": name,
        "released": true
    ])
}

private struct SendArguments {
    let window: String
    let recipient: String
    let confirmation: String
}

private func parseSendArguments(_ arguments: [String]) throws -> SendArguments {
    var values: [String: String] = [:]
    var index = 0
    let accepted = Set(["--window", "--recipient", "--confirm-recipient"])
    while index < arguments.count {
        let flag = arguments[index]
        guard accepted.contains(flag) else {
            throw CommandError("invalid_send_argument", "Unknown or misplaced send argument.", details: ["argument": flag])
        }
        guard values[flag] == nil else {
            throw CommandError("duplicate_send_argument", "A send option was provided more than once.", details: ["option": flag])
        }
        guard index + 1 < arguments.count else {
            throw CommandError("missing_send_value", "A send option is missing its value.", details: ["option": flag])
        }
        let value = arguments[index + 1]
        guard !value.isEmpty, !accepted.contains(value) else {
            throw CommandError("empty_send_value", "A send option has an empty value.", details: ["option": flag])
        }
        values[flag] = value
        index += 2
    }
    guard let window = values["--window"],
          let recipient = values["--recipient"],
          let confirmation = values["--confirm-recipient"] else {
        throw CommandError("missing_send_argument", "send requires --window, --recipient, and --confirm-recipient exactly once.")
    }
    guard recipient == confirmation else {
        throw CommandError("recipient_confirmation_mismatch", "--confirm-recipient must exactly match --recipient.")
    }
    guard !recipient.localizedCaseInsensitiveContains("[redacted-email]"), !containsEmailAddress(recipient) else {
        throw CommandError("recipient_redacted", "Email-looking or redacted Accessibility labels cannot be targeted by send.")
    }
    return SendArguments(window: window, recipient: recipient, confirmation: confirmation)
}

private func uniqueChooserWindow(application: AXUIElement, exactTitle: String) throws -> AXUIElement {
    let matches = axWindows(application).filter { windowTitle($0) == exactTitle }
    guard matches.count == 1, let window = matches.first else {
        throw CommandError(
            matches.isEmpty ? "chooser_window_not_found" : "chooser_window_ambiguous",
            matches.isEmpty ? "No Blip window exactly matched --window." : "More than one Blip window exactly matched --window.",
            details: ["window": redactEmails(exactTitle), "matchingWindowCount": matches.count]
        )
    }
    return window
}

private struct VerifiedRecipientRow {
    let row: AXUIElement
    let frame: CGRect
}

private func isDescendant(_ element: AXUIElement, of ancestor: AXUIElement, stopAt application: AXUIElement? = nil) -> Bool {
    var current: AXUIElement? = element
    var steps = 0
    while let candidate = current, steps < maximumAXDepth + 4 {
        if sameElement(candidate, ancestor) { return true }
        if let application, sameElement(candidate, application) { return false }
        current = axElementAttribute(candidate, kAXParentAttribute as String)
        steps += 1
    }
    return false
}

private func verifyChooserRecipient(window: AXUIElement, recipient: String) throws -> VerifiedRecipientRow {
    let tree = buildAXTree(from: [window])
    guard !tree.truncated else {
        throw CommandError(
            "chooser_inspection_incomplete",
            "The chooser exceeded the bounded Accessibility inspection limit; selection was refused.",
            details: ["maximumDepth": maximumAXDepth, "maximumElements": maximumAXElements]
        )
    }

    let staticLabels: [(Int, String)] = tree.nodes.enumerated().compactMap { index, node in
        guard let value = labelForStaticText(node) else { return nil }
        return (index, value)
    }
    guard staticLabels.contains(where: { $0.1 == "To:" }) else {
        throw CommandError("not_a_pending_chooser", "The exact-title window has no static 'To:' label; it was not treated as a pending Blip file chooser.")
    }

    let matchingLabels = staticLabels.filter { $0.1 == recipient }
    guard matchingLabels.count == 1, let match = matchingLabels.first else {
        throw CommandError(
            matchingLabels.isEmpty ? "recipient_not_found" : "recipient_ambiguous",
            matchingLabels.isEmpty ? "No static recipient label exactly matched --recipient." : "More than one static recipient label exactly matched --recipient.",
            details: ["recipient": redactEmails(recipient), "matchingLabelCount": matchingLabels.count]
        )
    }
    guard let rowIndex = nearestRowIndex(for: match.0, in: tree),
          hasListContext(rowIndex, in: tree),
          let frame = tree.nodes[rowIndex].frame else {
        throw CommandError("recipient_row_uninspectable", "The exact recipient label was not inside a bounded, inspectable recipient row.")
    }

    let row = tree.nodes[rowIndex]
    guard row.role != (kAXWindowRole as String),
          !isDescendant(tree.nodes[staticLabels.first(where: { $0.1 == "To:" })!.0].element, of: row.element) else {
        throw CommandError("not_a_pending_chooser", "The recipient label and 'To:' prompt did not form separate chooser regions.")
    }

    let allRecipientRows = recipientRows(in: tree)
    guard allRecipientRows.contains(where: { sameElement($0.element, row.element) && $0.name == recipient }) else {
        throw CommandError("recipient_row_uninspectable", "The exact label could not be reclassified as a live recipient row.")
    }

    let distinctMatchingGroups = allRecipientRows.filter { $0.name == recipient }.reduce(into: [AXUIElement]()) { groups, candidate in
        if !groups.contains(where: { sameElement($0, candidate.element) }) { groups.append(candidate.element) }
    }
    guard distinctMatchingGroups.count == 1 else {
        throw CommandError("recipient_ambiguous", "The recipient appeared in more than one Accessibility row group.", details: ["matchingGroupCount": distinctMatchingGroups.count])
    }
    return VerifiedRecipientRow(row: row.element, frame: frame)
}

private func freshRowLabels(_ row: AXUIElement) throws -> [String] {
    let tree = buildAXTree(from: [row], maxDepth: 6, maxCount: 100)
    guard !tree.truncated else {
        throw CommandError("recipient_row_changed", "The recipient row became too complex to verify immediately before clicking.")
    }
    return tree.nodes.compactMap(labelForStaticText)
}

private func commandSend(_ arguments: [String]) throws {
    let options = try parseSendArguments(arguments)
    try requireTrustedAccessibility()
    let (runningApplication, application) = try requireSingleRunningBlip()

    var window = try uniqueChooserWindow(application: application, exactTitle: options.window)
    _ = try verifyChooserRecipient(window: window, recipient: options.recipient)

    runningApplication.activate(options: [])
    guard AXUIElementSetAttributeValue(window, kAXFocusedAttribute as CFString, kCFBooleanTrue) == .success else {
        throw CommandError("chooser_focus_failed", "Could not focus the verified chooser window; no click was issued.")
    }
    usleep(80_000)

    // Re-resolve every UI object after focus so no stale element or coordinate is reused.
    window = try uniqueChooserWindow(application: application, exactTitle: options.window)
    let verified = try verifyChooserRecipient(window: window, recipient: options.recipient)
    guard let freshFrame = axFrame(verified.row), freshFrame == verified.frame else {
        throw CommandError("recipient_row_changed", "The recipient row moved or changed while it was being verified; no click was issued.")
    }

    let labelsImmediatelyBeforeClick = try freshRowLabels(verified.row)
    guard labelsImmediatelyBeforeClick.filter({ $0 == options.recipient }).count == 1 else {
        throw CommandError("recipient_row_changed", "The exact recipient label was no longer unique inside its row; no click was issued.")
    }

    let clickPoint = CGPoint(x: freshFrame.midX, y: freshFrame.midY)
    var hitElement: AXUIElement?
    guard AXUIElementCopyElementAtPosition(AXUIElementCreateSystemWide(), Float(clickPoint.x), Float(clickPoint.y), &hitElement) == .success,
          let hitElement else {
        throw CommandError("hit_test_failed", "Accessibility could not identify the UI target at the fresh recipient-row coordinates; no click was issued.")
    }
    var hitPID: pid_t = 0
    guard AXUIElementGetPid(hitElement, &hitPID) == .success,
          hitPID == runningApplication.processIdentifier,
          isDescendant(hitElement, of: verified.row, stopAt: application) else {
        throw CommandError("hit_test_mismatch", "The fresh hit-test target did not belong to the exact matching Blip recipient row; no click was issued.")
    }

    guard let source = CGEventSource(stateID: .hidSystemState),
          let down = CGEvent(mouseEventSource: source, mouseType: .leftMouseDown, mouseCursorPosition: clickPoint, mouseButton: .left),
          let up = CGEvent(mouseEventSource: source, mouseType: .leftMouseUp, mouseCursorPosition: clickPoint, mouseButton: .left) else {
        throw CommandError("mouse_event_creation_failed", "Could not create the recipient click; no event was posted.")
    }
    down.post(tap: .cghidEventTap)
    up.post(tap: .cghidEventTap)

    emit([
        "ok": true,
        "command": "send",
        "window": redactEmails(options.window),
        "recipient": redactEmails(options.recipient),
        "state": "recipient-click-issued",
        "note": "A single verified recipient-row click was issued. This does not prove transfer acceptance or delivery. Inspect status and preserve its raw text."
    ])
}

private let usage = """
Usage:
  swift blip.swift doctor
  swift blip.swift request-permission
  swift blip.swift devices
  swift blip.swift prepare ABSOLUTE_PATH [ABSOLUTE_PATH ...]
  swift blip.swift status
  swift blip.swift send --window EXACT --recipient EXACT --confirm-recipient EXACT
  swift blip.swift release-pasteboard CFPasteboardUnique-NAME
  swift blip.swift --help

Safety:
  prepare opens a Blip chooser but never selects a recipient.
  send performs one fail-closed click only after exact live AX verification.
  status reports raw window text and never infers delivery.
"""

private func run() throws {
    let arguments = Array(CommandLine.arguments.dropFirst())
    guard let command = arguments.first else {
        throw CommandError("missing_command", "A command is required. Use --help for syntax.")
    }
    let rest = Array(arguments.dropFirst())
    switch command {
    case "--help", "-h", "help":
        guard rest.isEmpty else { throw CommandError("unexpected_argument", "--help accepts no additional arguments.") }
        print(usage)
    case "doctor":
        guard rest.isEmpty else { throw CommandError("unexpected_argument", "doctor accepts no arguments.") }
        commandDoctor()
    case "request-permission":
        guard rest.isEmpty else { throw CommandError("unexpected_argument", "request-permission accepts no arguments.") }
        try commandRequestPermission()
    case "devices":
        guard rest.isEmpty else { throw CommandError("unexpected_argument", "devices accepts no arguments.") }
        try commandDevices()
    case "prepare":
        try commandPrepare(paths: rest)
    case "status":
        guard rest.isEmpty else { throw CommandError("unexpected_argument", "status accepts no arguments.") }
        try commandStatus()
    case "send":
        try commandSend(rest)
    case "release-pasteboard":
        guard rest.count == 1, let name = rest.first else {
            throw CommandError("invalid_release_arguments", "release-pasteboard requires exactly one pasteboard name.")
        }
        try commandReleasePasteboard(name)
    default:
        throw CommandError("unknown_command", "Unknown command. Use --help for syntax.", details: ["command": command])
    }
}

do {
    try run()
} catch let error as CommandError {
    fail(error)
} catch {
    fail(CommandError("unexpected_error", "Unexpected error: \(error.localizedDescription)"))
}
